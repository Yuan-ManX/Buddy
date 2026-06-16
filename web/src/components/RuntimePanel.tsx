import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface RuntimeInfo {
  agent_id: string;
  agent_name: string;
  state: string;
  executions: number;
  uptime: number;
}

interface RuntimeStats {
  agent_id: string;
  agent_name: string;
  state: string;
  uptime_seconds: number;
  executions: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number;
  };
  performance: {
    avg_response_time_ms: number;
    avg_tokens_per_execution: number;
    total_tokens_used: number;
    total_tool_calls: number;
    total_tool_errors: number;
  };
  resources: {
    token_budget_remaining: number;
    token_budget_total: number;
    token_budget_percent: number;
    active_executions: number;
    max_parallel_tasks: number;
  };
  checkpoints: number;
  event_listeners: number;
}

interface RuntimeExecution {
  id: string;
  mode: string;
  prompt: string;
  success: boolean;
  tokens_used: number;
  tool_calls: number;
  elapsed: string;
  error: string;
}

interface SystemDashboard {
  timestamp: string;
  runtime: {
    active_runtimes: number;
    total_executions: number;
    runtimes: RuntimeInfo[];
  };
  platform: any;
  costs: any;
  synthesis: any;
  guard: any;
  pulse: any;
}

export const RuntimePanel: React.FC = () => {
  const [runtimes, setRuntimes] = useState<RuntimeInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [runtimeStats, setRuntimeStats] = useState<RuntimeStats | null>(null);
  const [executions, setExecutions] = useState<RuntimeExecution[]>([]);
  const [dashboard, setDashboard] = useState<SystemDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'agent' | 'dashboard'>('overview');

  const loadRegistry = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.runtime.registry();
      setRuntimes(data.runtimes || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load runtime registry');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAgentStats = useCallback(async (agentId: string) => {
    try {
      setLoading(true);
      setError(null);
      const [stats, execs] = await Promise.all([
        api.runtime.stats(agentId),
        api.runtime.executions(agentId, 20),
      ]);
      setRuntimeStats(stats);
      setExecutions(execs.executions || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load agent stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.runtime.dashboard();
      setDashboard(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRegistry();
  }, [loadRegistry]);

  useEffect(() => {
    if (selectedAgent) {
      loadAgentStats(selectedAgent);
    }
  }, [selectedAgent, loadAgentStats]);

  const handlePause = async (agentId: string) => {
    try {
      await api.runtime.pause(agentId);
      loadRegistry();
      if (selectedAgent === agentId) loadAgentStats(agentId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to pause runtime');
    }
  };

  const handleResume = async (agentId: string) => {
    try {
      await api.runtime.resume(agentId);
      loadRegistry();
      if (selectedAgent === agentId) loadAgentStats(agentId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to resume runtime');
    }
  };

  const handleRefill = async (agentId: string) => {
    try {
      await api.runtime.refillTokens(agentId, 10000);
      if (selectedAgent === agentId) loadAgentStats(agentId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to refill tokens');
    }
  };

  const handleShutdown = async (agentId: string) => {
    if (!confirm('Shutdown this runtime?')) return;
    try {
      await api.runtime.shutdown(agentId);
      setSelectedAgent('');
      setRuntimeStats(null);
      loadRegistry();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to shutdown runtime');
    }
  };

  const stateColor = (state: string) => {
    switch (state) {
      case 'ready': return '#10b981';
      case 'running': return '#3b82f6';
      case 'paused': return '#f59e0b';
      case 'error': return '#ef4444';
      case 'stopped': return '#6b7280';
      default: return '#9ca3af';
    }
  };

  if (loading && !runtimeStats && !dashboard) {
    return <div className="panel-loading">Loading runtime data...</div>;
  }

  return (
    <div className="runtime-panel">
      <div className="panel-header">
        <h2>Agent Runtime</h2>
        <div className="panel-header-actions">
          <button
            className={`btn btn-sm ${activeSection === 'overview' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setActiveSection('overview'); loadRegistry(); }}
          >
            Overview
          </button>
          <button
            className={`btn btn-sm ${activeSection === 'agent' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('agent')}
          >
            Agent Detail
          </button>
          <button
            className={`btn btn-sm ${activeSection === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setActiveSection('dashboard'); loadDashboard(); }}
          >
            Dashboard
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {/* Overview Section */}
      {activeSection === 'overview' && (
        <div className="runtime-overview">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{runtimes.length}</div>
              <div className="stat-label">Active Runtimes</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {runtimes.reduce((sum, r) => sum + r.executions, 0)}
              </div>
              <div className="stat-label">Total Executions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {runtimes.filter(r => r.state === 'running').length}
              </div>
              <div className="stat-label">Running</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {runtimes.filter(r => r.state === 'error').length}
              </div>
              <div className="stat-label">Errors</div>
            </div>
          </div>

          <div className="runtime-list">
            <h3>Runtime Instances</h3>
            {runtimes.length === 0 ? (
              <div className="panel-empty">No active runtimes. Create an agent to start.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>State</th>
                    <th>Executions</th>
                    <th>Uptime</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {runtimes.map((rt) => (
                    <tr key={rt.agent_id}>
                      <td>
                        <button
                          className="link-btn"
                          onClick={() => { setSelectedAgent(rt.agent_id); setActiveSection('agent'); }}
                        >
                          {rt.agent_name}
                        </button>
                        <div className="text-muted" style={{ fontSize: '0.75rem' }}>{rt.agent_id}</div>
                      </td>
                      <td>
                        <span className="status-badge" style={{ background: stateColor(rt.state) }}>
                          {rt.state}
                        </span>
                      </td>
                      <td>{rt.executions}</td>
                      <td>{Math.floor(rt.uptime / 60)}m</td>
                      <td>
                        <div className="btn-group">
                          {rt.state === 'running' && (
                            <button className="btn btn-xs btn-warning" onClick={() => handlePause(rt.agent_id)}>
                              Pause
                            </button>
                          )}
                          {rt.state === 'paused' && (
                            <button className="btn btn-xs btn-success" onClick={() => handleResume(rt.agent_id)}>
                              Resume
                            </button>
                          )}
                          <button className="btn btn-xs btn-danger" onClick={() => handleShutdown(rt.agent_id)}>
                            Stop
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Agent Detail Section */}
      {activeSection === 'agent' && (
        <div className="runtime-agent-detail">
          {!selectedAgent ? (
            <div className="panel-empty">Select an agent from the overview to view details.</div>
          ) : runtimeStats ? (
            <div>
              <div className="agent-header">
                <h3>{runtimeStats.agent_name}</h3>
                <span className="status-badge" style={{ background: stateColor(runtimeStats.state) }}>
                  {runtimeStats.state}
                </span>
                <span className="text-muted" style={{ fontSize: '0.8rem' }}>{runtimeStats.agent_id}</span>
              </div>

              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{runtimeStats.executions.total}</div>
                  <div className="stat-label">Total Executions</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: '#10b981' }}>
                    {runtimeStats.executions.success_rate}%
                  </div>
                  <div className="stat-label">Success Rate</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{runtimeStats.performance.total_tokens_used.toLocaleString()}</div>
                  <div className="stat-label">Tokens Used</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{runtimeStats.performance.total_tool_calls}</div>
                  <div className="stat-label">Tool Calls</div>
                </div>
              </div>

              <div className="section">
                <h4>Performance</h4>
                <div className="metric-row">
                  <span>Avg Response Time</span>
                  <span>{runtimeStats.performance.avg_response_time_ms}ms</span>
                </div>
                <div className="metric-row">
                  <span>Avg Tokens / Execution</span>
                  <span>{runtimeStats.performance.avg_tokens_per_execution}</span>
                </div>
                <div className="metric-row">
                  <span>Tool Errors</span>
                  <span>{runtimeStats.performance.total_tool_errors}</span>
                </div>
              </div>

              <div className="section">
                <h4>Resources</h4>
                <div className="progress-bar-container">
                  <div className="progress-bar-label">
                    Token Budget: {runtimeStats.resources.token_budget_remaining.toLocaleString()} / {runtimeStats.resources.token_budget_total.toLocaleString()}
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${100 - runtimeStats.resources.token_budget_percent}%`,
                        background: runtimeStats.resources.token_budget_percent < 10 ? '#ef4444' : '#3b82f6',
                      }}
                    />
                  </div>
                </div>
                <div className="metric-row">
                  <span>Active Executions</span>
                  <span>{runtimeStats.resources.active_executions} / {runtimeStats.resources.max_parallel_tasks}</span>
                </div>
                <div style={{ marginTop: '0.5rem' }}>
                  <button className="btn btn-sm btn-primary" onClick={() => handleRefill(selectedAgent)}>
                    Refill Tokens
                  </button>
                </div>
              </div>

              <div className="section">
                <h4>Recent Executions</h4>
                {executions.length === 0 ? (
                  <div className="panel-empty">No executions recorded.</div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Mode</th>
                        <th>Prompt</th>
                        <th>Status</th>
                        <th>Tokens</th>
                        <th>Tools</th>
                      </tr>
                    </thead>
                    <tbody>
                      {executions.slice(0, 10).map((exec) => (
                        <tr key={exec.id}>
                          <td><span className="badge">{exec.mode}</span></td>
                          <td className="text-truncate" style={{ maxWidth: '300px' }}>{exec.prompt}</td>
                          <td>
                            <span style={{ color: exec.success ? '#10b981' : '#ef4444' }}>
                              {exec.success ? 'OK' : 'FAIL'}
                            </span>
                          </td>
                          <td>{exec.tokens_used}</td>
                          <td>{exec.tool_calls}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          ) : (
            <div className="panel-loading">Loading agent stats...</div>
          )}
        </div>
      )}

      {/* Dashboard Section */}
      {activeSection === 'dashboard' && (
        <div className="runtime-dashboard">
          {dashboard ? (
            <div>
              <div className="dashboard-header">
                <h3>System Dashboard</h3>
                <span className="text-muted">{new Date(dashboard.timestamp).toLocaleString()}</span>
              </div>

              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{dashboard.runtime.active_runtimes}</div>
                  <div className="stat-label">Active Runtimes</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{dashboard.runtime.total_executions}</div>
                  <div className="stat-label">Total Executions</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {dashboard.synthesis?.active_agents || 0}
                  </div>
                  <div className="stat-label">Synthesis Agents</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {dashboard.costs?.total_cost ? `$${dashboard.costs.total_cost.toFixed(4)}` : 'N/A'}
                  </div>
                  <div className="stat-label">Total Cost</div>
                </div>
              </div>

              <div className="section">
                <h4>Platform</h4>
                <pre className="json-preview">{JSON.stringify(dashboard.platform, null, 2)}</pre>
              </div>

              <div className="section">
                <h4>Costs</h4>
                <pre className="json-preview">{JSON.stringify(dashboard.costs, null, 2)}</pre>
              </div>

              <div className="section">
                <h4>Synthesis</h4>
                <pre className="json-preview">{JSON.stringify(dashboard.synthesis, null, 2)}</pre>
              </div>
            </div>
          ) : (
            <div className="panel-loading">Loading dashboard...</div>
          )}
        </div>
      )}
    </div>
  );
};