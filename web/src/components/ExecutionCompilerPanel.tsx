import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface CompilePlan {
  plan_id: string;
  name: string;
  description: string;
  status: string;
  graph_count: number;
  created_at: string;
  updated_at: string;
}

interface CompiledGraph {
  graph_id: string;
  plan_id: string;
  name: string;
  node_count: number;
  edge_count: number;
  status: string;
  compiled_at: string;
}

interface ExecutionCompilerStats {
  total_plans: number;
  total_graphs: number;
  total_executions: number;
  success_rate: number;
  average_compile_time_ms: number;
  cached_graphs: number;
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

export const ExecutionCompilerPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<ExecutionCompilerStats | null>(null);
  const [plans, setPlans] = useState<CompilePlan[]>([]);
  const [graphs, setGraphs] = useState<CompiledGraph[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'compile' | 'graphs' | 'plans'>('overview');

  // Compile form
  const [compileForm, setCompileForm] = useState({
    name: '',
    description: '',
    source_code: '',
    target: 'default',
    optimization_level: 'standard',
  });
  const [compiling, setCompiling] = useState(false);

  // Execute form
  const [executing, setExecuting] = useState(false);
  const [executeGraphId, setExecuteGraphId] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, g, p] = await Promise.all([
        request<ExecutionCompilerStats>('/execution-compiler/stats').catch(() => null),
        request<CompiledGraph[]>('/execution-compiler/graphs').catch(() => []),
        request<CompilePlan[]>('/execution-compiler/graphs').catch(() => []),
      ]);
      setStats(s);
      setGraphs(Array.isArray(g) ? g : (g as any)?.graphs || []);
      setPlans(Array.isArray(p) ? p : (p as any)?.plans || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load execution compiler data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCompile = async () => {
    if (!compileForm.name.trim() || !compileForm.source_code.trim()) return;
    try {
      setCompiling(true);
      const result = await request<any>('/execution-compiler/compile', {
        method: 'POST',
        body: JSON.stringify({
          name: compileForm.name,
          description: compileForm.description || undefined,
          source_code: compileForm.source_code,
          target: compileForm.target,
          optimization_level: compileForm.optimization_level,
        }),
      });
      toast.success(result.message || 'Compile plan created successfully');
      setCompileForm({ name: '', description: '', source_code: '', target: 'default', optimization_level: 'standard' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setCompiling(false);
    }
  };

  const handleExecute = async () => {
    if (!executeGraphId.trim()) return;
    try {
      setExecuting(true);
      const result = await request<any>(`/execution-compiler/graphs/${executeGraphId}/execute`, {
        method: 'POST',
      });
      toast.success(result.message || 'Graph executed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setExecuting(false);
    }
  };

  const statusColors: Record<string, string> = {
    compiled: '#22c55e',
    compiling: '#3b82f6',
    failed: '#ef4444',
    pending: '#f59e0b',
    cached: '#8b5cf6',
    executed: '#06b6d4',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Execution Compiler</h2>
          <p className="panel-subtitle">Compile execution plans into optimized computation graphs</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading execution compiler data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Execution Compiler</h2>
        <p className="panel-subtitle">Compile, optimize, and execute computation graphs from high-level plans</p>
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
              <span className="stat-value">{stats.total_plans}</span>
              <span className="stat-label">Total Plans</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.total_graphs}</span>
              <span className="stat-label">Total Graphs</span>
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
              <span className="stat-value" style={{ color: stats.success_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                {(stats.success_rate * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Success Rate</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.cached_graphs}</span>
              <span className="stat-label">Cached</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'compile', 'graphs', 'plans'] as const).map(s => (
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
              <h3>Compiler Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Plans</span>
                <strong>{stats.total_plans}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Graphs</span>
                <strong style={{ color: '#22c55e' }}>{stats.total_graphs}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Executions</span>
                <strong style={{ color: '#3b82f6' }}>{stats.total_executions}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Success Rate</span>
                <strong style={{ color: stats.success_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                  {(stats.success_rate * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Avg Compile Time</span>
                <strong>{stats.average_compile_time_ms?.toFixed(1)}ms</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Cached Graphs</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.cached_graphs}</strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Recent Graphs</h3>
              {graphs.length === 0 ? (
                <div className="panel-empty">No graphs compiled yet</div>
              ) : (
                <div className="forge-skill-list">
                  {graphs.slice(0, 5).map(graph => (
                    <div key={graph.graph_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{graph.name}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[graph.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {graph.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Nodes: {graph.node_count} | Edges: {graph.edge_count}</div>
                        <div>Compiled: {new Date(graph.compiled_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Compile Section ── */}
      {activeSection === 'compile' && (
        <div className="dashboard-section">
          <h3>Create Compile Plan</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Plan Name</label>
              <input
                type="text"
                value={compileForm.name}
                onChange={e => setCompileForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Compile Plan"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={2}
                value={compileForm.description}
                onChange={e => setCompileForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this plan should accomplish"
              />
            </div>
            <div className="form-group">
              <label>Source Code / Definition</label>
              <textarea
                rows={6}
                value={compileForm.source_code}
                onChange={e => setCompileForm(f => ({ ...f, source_code: e.target.value }))}
                placeholder="Enter the source code or execution definition to compile"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Target</label>
                <select
                  value={compileForm.target}
                  onChange={e => setCompileForm(f => ({ ...f, target: e.target.value }))}
                >
                  <option value="default">Default</option>
                  <option value="cpu">CPU</option>
                  <option value="gpu">GPU</option>
                  <option value="wasm">WebAssembly</option>
                  <option value="distributed">Distributed</option>
                </select>
              </div>
              <div className="form-group">
                <label>Optimization Level</label>
                <select
                  value={compileForm.optimization_level}
                  onChange={e => setCompileForm(f => ({ ...f, optimization_level: e.target.value }))}
                >
                  <option value="none">None</option>
                  <option value="standard">Standard</option>
                  <option value="aggressive">Aggressive</option>
                </select>
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleCompile}
              disabled={compiling || !compileForm.name.trim() || !compileForm.source_code.trim()}
            >
              {compiling ? 'Compiling...' : 'Compile Plan'}
            </button>
          </div>
        </div>
      )}

      {/* ── Graphs Section ── */}
      {activeSection === 'graphs' && (
        <div className="dashboard-section">
          <h3>Compiled Graphs ({graphs.length})</h3>

          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Execute Graph by ID</label>
                <input
                  type="text"
                  value={executeGraphId}
                  onChange={e => setExecuteGraphId(e.target.value)}
                  placeholder="Enter graph ID..."
                />
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button
                  className="btn-primary"
                  onClick={handleExecute}
                  disabled={executing || !executeGraphId.trim()}
                  style={{ background: '#06b6d4' }}
                >
                  {executing ? 'Executing...' : 'Execute'}
                </button>
              </div>
            </div>
          </div>

          {graphs.length === 0 ? (
            <div className="panel-empty">No graphs compiled yet. Go to the Compile tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {graphs.map(graph => (
                <div key={graph.graph_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{graph.name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[graph.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {graph.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Nodes: {graph.node_count} | Edges: {graph.edge_count}</div>
                    <div>Plan ID: {graph.plan_id}</div>
                    <div>Compiled: {new Date(graph.compiled_at).toLocaleString()}</div>
                    <div>Graph ID: {graph.graph_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Plans Section ── */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <h3>Compile Plans ({plans.length})</h3>
          {plans.length === 0 ? (
            <div className="panel-empty">No compile plans yet. Go to the Compile tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {plans.map(plan => (
                <div key={plan.plan_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{plan.name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[plan.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {plan.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{plan.description}</div>
                    <div>Graphs: {plan.graph_count} | Status: {plan.status}</div>
                    <div>Created: {new Date(plan.created_at).toLocaleString()}</div>
                    <div>Updated: {new Date(plan.updated_at).toLocaleString()}</div>
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

export default ExecutionCompilerPanel;