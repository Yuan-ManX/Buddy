import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface ModelEndpoint {
  endpoint_id: string;
  model_name: string;
  provider: string;
  status: string;
  latency_ms: number;
  cost_per_token: number;
  capabilities: string[];
  created_at: string;
}

interface ModelExecution {
  execution_id: string;
  endpoint_id: string;
  model_name: string;
  status: string;
  tokens_used: number;
  cost: number;
  duration_ms: number;
  started_at: string;
  completed_at: string | null;
}

interface ModelConductorStats {
  total_endpoints: number;
  active_endpoints: number;
  total_executions: number;
  total_tokens: number;
  total_cost: number;
  average_latency_ms: number;
  health_status: string;
}

interface HealthStatus {
  status: string;
  healthy_endpoints: number;
  unhealthy_endpoints: number;
  last_checked: string;
}

// ── Request helper ──

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

// ── Component ──

export const ModelConductorPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<ModelConductorStats | null>(null);
  const [endpoints, setEndpoints] = useState<ModelEndpoint[]>([]);
  const [executions, setExecutions] = useState<ModelExecution[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'route' | 'endpoints' | 'executions'>('overview');

  // Route form
  const [routeForm, setRouteForm] = useState({
    prompt: '',
    preferred_model: '',
    max_tokens: 1024,
    temperature: 0.7,
    strategy: 'best',
  });
  const [routing, setRouting] = useState(false);
  const [routeResult, setRouteResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, ep, ex, h] = await Promise.all([
        request<ModelConductorStats>('/model-conductor/stats').catch(() => null),
        request<ModelEndpoint[]>('/model-conductor/endpoints').catch(() => []),
        request<ModelExecution[]>('/model-conductor/route').catch(() => []),
        request<HealthStatus>('/model-conductor/stats').catch(() => null),
      ]);
      setStats(s);
      setEndpoints(Array.isArray(ep) ? ep : (ep as any)?.endpoints || []);
      setExecutions(Array.isArray(ex) ? ex : (ex as any)?.executions || []);
      setHealth(h);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load model conductor data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRoute = async () => {
    if (!routeForm.prompt.trim()) return;
    try {
      setRouting(true);
      setRouteResult(null);
      const result = await request<any>('/model-conductor/route', {
        method: 'POST',
        body: JSON.stringify({
          prompt: routeForm.prompt,
          preferred_model: routeForm.preferred_model || undefined,
          max_tokens: routeForm.max_tokens,
          temperature: routeForm.temperature,
          strategy: routeForm.strategy,
        }),
      });
      setRouteResult(result);
      toast.success(result.message || 'Request routed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRouting(false);
    }
  };

  const handleHealthCheck = async () => {
    try {
      const result = await request<HealthStatus>('/model-conductor/stats', { method: 'POST' });
      setHealth(result);
      toast.success(`Health check: ${result.status}`);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    healthy: '#22c55e',
    degraded: '#f59e0b',
    unhealthy: '#ef4444',
    offline: '#9ca3af',
    running: '#3b82f6',
    completed: '#22c55e',
    failed: '#ef4444',
    pending: '#f59e0b',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Model Conductor</h2>
          <p className="panel-subtitle">Multi-model orchestration and intelligent routing</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading model conductor data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Model Conductor</h2>
        <p className="panel-subtitle">Route requests across multiple AI models with intelligent selection</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_endpoints}</span>
              <span className="stat-label">Endpoints</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_endpoints}</span>
              <span className="stat-label">Active</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.total_executions}</span>
              <span className="stat-label">Executions</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>
                {stats.total_tokens >= 1000 ? `${(stats.total_tokens / 1000).toFixed(1)}k` : stats.total_tokens}
              </span>
              <span className="stat-label">Tokens</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>${stats.total_cost?.toFixed(4)}</span>
              <span className="stat-label">Cost</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'route', 'endpoints', 'executions'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Conductor Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Endpoints</span>
                <strong>{stats.total_endpoints}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Active Endpoints</span>
                <strong style={{ color: '#22c55e' }}>{stats.active_endpoints}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Executions</span>
                <strong style={{ color: '#3b82f6' }}>{stats.total_executions}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Tokens</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.total_tokens?.toLocaleString()}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Cost</span>
                <strong style={{ color: '#f59e0b' }}>${stats.total_cost?.toFixed(4)}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Avg Latency</span>
                <strong>{stats.average_latency_ms?.toFixed(1)}ms</strong>
              </div>

              <div style={{ marginTop: 20, display: 'flex', gap: 8, alignItems: 'center' }}>
                <button
                  className="btn-primary"
                  onClick={handleHealthCheck}
                  style={{ background: '#06b6d4' }}
                >
                  Run Health Check
                </button>
                {health && (
                  <span className="dashboard-badge" style={{
                    background: statusColors[health.status] || '#9ca3af',
                    color: '#fff',
                  }}>
                    {health.status} ({health.healthy_endpoints}/{health.healthy_endpoints + health.unhealthy_endpoints} healthy)
                  </span>
                )}
              </div>

              <h3 style={{ marginTop: 24 }}>Endpoints</h3>
              {endpoints.length === 0 ? (
                <div className="panel-empty">No endpoints configured</div>
              ) : (
                <div className="forge-skill-list">
                  {endpoints.slice(0, 5).map(ep => (
                    <div key={ep.endpoint_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{ep.model_name}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[ep.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {ep.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Provider: {ep.provider} | Latency: {ep.latency_ms}ms</div>
                        <div>Cost: ${ep.cost_per_token?.toExponential(2)}/token</div>
                        {ep.capabilities && (
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                            {ep.capabilities.map((cap, i) => (
                              <span key={i} style={{
                                padding: '2px 8px',
                                background: '#e8eaf6',
                                color: '#4f6ef7',
                                borderRadius: 12,
                                fontSize: '0.7rem',
                              }}>
                                {cap}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Route Section ── */}
      {activeSection === 'route' && (
        <div className="dashboard-section">
          <h3>Route Request</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Prompt</label>
              <textarea
                rows={4}
                value={routeForm.prompt}
                onChange={e => setRouteForm(f => ({ ...f, prompt: e.target.value }))}
                placeholder="Enter your prompt to route to the best available model..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Preferred Model</label>
                <select
                  value={routeForm.preferred_model}
                  onChange={e => setRouteForm(f => ({ ...f, preferred_model: e.target.value }))}
                >
                  <option value="">Auto-select</option>
                  {endpoints.map(ep => (
                    <option key={ep.endpoint_id} value={ep.model_name}>{ep.model_name} ({ep.provider})</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Routing Strategy</label>
                <select
                  value={routeForm.strategy}
                  onChange={e => setRouteForm(f => ({ ...f, strategy: e.target.value }))}
                >
                  <option value="best">Best Available</option>
                  <option value="cheapest">Cheapest</option>
                  <option value="fastest">Fastest</option>
                  <option value="round_robin">Round Robin</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Max Tokens</label>
                <input
                  type="number"
                  min={1}
                  max={32768}
                  value={routeForm.max_tokens}
                  onChange={e => setRouteForm(f => ({ ...f, max_tokens: parseInt(e.target.value) || 1024 }))}
                />
              </div>
              <div className="form-group">
                <label>Temperature</label>
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={routeForm.temperature}
                  onChange={e => setRouteForm(f => ({ ...f, temperature: parseFloat(e.target.value) || 0.7 }))}
                />
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleRoute}
              disabled={routing || !routeForm.prompt.trim()}
            >
              {routing ? 'Routing...' : 'Route Request'}
            </button>
          </div>

          {routeResult && (
            <div style={{
              marginTop: 20,
              padding: 16,
              background: '#f8fafc',
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}>
              <h4>Route Result</h4>
              <div style={{ marginTop: 8, fontSize: '0.9rem', color: '#475569' }}>
                {routeResult.model && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Routed to:</strong>{' '}
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      background: '#4f6ef7',
                      color: '#fff',
                      borderRadius: 4,
                      fontSize: '0.8rem',
                    }}>
                      {routeResult.model}
                    </span>
                  </div>
                )}
                {routeResult.tokens_used !== undefined && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Tokens Used:</strong> {routeResult.tokens_used}
                  </div>
                )}
                {routeResult.cost !== undefined && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Cost:</strong> ${routeResult.cost?.toFixed(6)}
                  </div>
                )}
                {routeResult.duration_ms !== undefined && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Duration:</strong> {routeResult.duration_ms}ms
                  </div>
                )}
                {routeResult.response && (
                  <div style={{ marginTop: 8, padding: 8, background: '#fff', borderRadius: 4, border: '1px solid #e2e8f0' }}>
                    <strong>Response:</strong>
                    <div style={{ whiteSpace: 'pre-wrap', marginTop: 4, fontSize: '0.85rem' }}>
                      {routeResult.response}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Endpoints Section ── */}
      {activeSection === 'endpoints' && (
        <div className="dashboard-section">
          <h3>Model Endpoints ({endpoints.length})</h3>
          {endpoints.length === 0 ? (
            <div className="panel-empty">No endpoints configured</div>
          ) : (
            <div className="forge-skill-list">
              {endpoints.map(ep => (
                <div key={ep.endpoint_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{ep.model_name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[ep.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {ep.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Provider: {ep.provider} | Latency: {ep.latency_ms}ms</div>
                    <div>Cost: ${ep.cost_per_token?.toExponential(2)}/token</div>
                    {ep.capabilities && ep.capabilities.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                        {ep.capabilities.map((cap, i) => (
                          <span key={i} style={{
                            padding: '2px 8px',
                            background: '#e8eaf6',
                            color: '#4f6ef7',
                            borderRadius: 12,
                            fontSize: '0.7rem',
                          }}>
                            {cap}
                          </span>
                        ))}
                      </div>
                    )}
                    <div>Created: {new Date(ep.created_at).toLocaleString()}</div>
                    <div>Endpoint ID: {ep.endpoint_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Executions Section ── */}
      {activeSection === 'executions' && (
        <div className="dashboard-section">
          <h3>Recent Executions ({executions.length})</h3>
          {executions.length === 0 ? (
            <div className="panel-empty">No executions recorded yet</div>
          ) : (
            <div className="forge-skill-list">
              {executions.map(ex => (
                <div key={ex.execution_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{ex.model_name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[ex.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {ex.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Tokens: {ex.tokens_used} | Cost: ${ex.cost?.toFixed(6)}</div>
                    <div>Duration: {ex.duration_ms}ms</div>
                    <div>Started: {new Date(ex.started_at).toLocaleString()}</div>
                    {ex.completed_at && (
                      <div>Completed: {new Date(ex.completed_at).toLocaleString()}</div>
                    )}
                    <div>Execution ID: {ex.execution_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModelConductorPanel;