import React, { useState, useEffect } from 'react';
import type { DaemonStats, DaemonRuntime } from '../types';
import { api } from '../api/client';

export const DaemonPanel: React.FC = () => {
  const [stats, setStats] = useState<DaemonStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const s = await api.daemon.stats();
      setStats(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load daemon data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleStartAgent = async (agentId: string, agentName: string) => {
    try {
      await api.daemon.startAgent(agentId, agentName);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start daemon');
    }
  };

  const handleStopAgent = async (agentId: string) => {
    try {
      await api.daemon.stopAgent(agentId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop daemon');
    }
  };

  const handleRestartAgent = async (agentId: string) => {
    try {
      await api.daemon.restartAgent(agentId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart daemon');
    }
  };

  const handleStartAll = async () => {
    try {
      await api.daemon.startAll();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start all daemons');
    }
  };

  const handleStopAll = async () => {
    try {
      await api.daemon.stopAll();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop all daemons');
    }
  };

  const statusColors: Record<string, string> = {
    running: '#10b981',
    idle: '#f59e0b',
    starting: '#3b82f6',
    stopping: '#ef4444',
    stopped: '#94a3b8',
    hibernating: '#6366f1',
    error: '#ef4444',
  };

  const formatUptime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
  };

  if (loading) {
    return <div className="panel-container"><div className="panel-loading">Loading daemon data...</div></div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Agent Daemon Manager</h2>
          <div className="panel-subtitle">Background runtime orchestration & health monitoring</div>
        </div>
        <div className="panel-header-actions">
          <button className="btn-sm btn-success" onClick={handleStartAll}>Start All</button>
          <button className="btn-sm btn-danger" onClick={handleStopAll}>Stop All</button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Overview Stats */}
      {stats && (
        <>
          <div className="memory-stats-grid">
            <div className="memory-stat-card">
              <div className="memory-stat-value">{stats.active_agents}/{stats.total_agents}</div>
              <div className="memory-stat-label">Active / Total</div>
            </div>
            <div className="memory-stat-card">
              <div className="memory-stat-value">{stats.total_concurrency}</div>
              <div className="memory-stat-label">Total Concurrency</div>
            </div>
            <div className="memory-stat-card">
              <div className="memory-stat-value">{stats.max_total_concurrency}</div>
              <div className="memory-stat-label">Max Concurrency</div>
            </div>
            <div className="memory-stat-card">
              <div className="memory-stat-value">
                {stats.max_total_concurrency > 0 ? ((stats.total_concurrency / stats.max_total_concurrency) * 100).toFixed(0) : 0}%
              </div>
              <div className="memory-stat-label">Capacity Used</div>
            </div>
          </div>

          {/* Status Distribution */}
          <div className="dashboard-section">
            <h3>Status Distribution</h3>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              {Object.entries(stats.status_distribution).map(([status, count]) => (
                <div key={status} style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  padding: '6px 14px', borderRadius: '100px',
                  background: `${statusColors[status] || '#666'}15`, border: `1px solid ${statusColors[status] || '#666'}33`,
                }}>
                  <span style={{
                    width: '8px', height: '8px', borderRadius: '50%',
                    background: statusColors[status] || '#666',
                  }} />
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text)', textTransform: 'capitalize' }}>
                    {status}
                  </span>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: statusColors[status] || '#666' }}>
                    {count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Runtime Management */}
      <div className="dashboard-section">
        <h3>Agent Runtimes ({stats?.runtimes.length || 0})</h3>
        {stats && stats.runtimes.length === 0 ? (
          <div className="panel-empty">No agent runtimes active. Start daemons to see runtime information.</div>
        ) : (
          <div className="autopilot-list">
            {stats?.runtimes.map((runtime: DaemonRuntime) => (
              <div key={runtime.agent_id} className="autopilot-card" style={{
                borderLeft: `3px solid ${statusColors[runtime.status] || '#666'}`,
              }}>
                <div className="autopilot-card-header">
                  <span className="autopilot-card-status" style={{ background: statusColors[runtime.status] || '#666' }}>
                    {runtime.status}
                  </span>
                  <span className="autopilot-card-trigger">{runtime.agent_name}</span>
                  <span className="autopilot-card-runs">{runtime.agent_id}</span>
                </div>

                <div className="autopilot-card-template" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Uptime</div>
                    <div style={{ fontWeight: 600 }}>{formatUptime(runtime.uptime_seconds)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Tasks</div>
                    <div style={{ fontWeight: 600 }}>
                      <span style={{ color: '#10b981' }}>{runtime.tasks_completed}</span>
                      {' / '}
                      <span style={{ color: '#ef4444' }}>{runtime.tasks_failed}</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Success Rate</div>
                    <div style={{ fontWeight: 600 }}>{(runtime.success_rate * 100).toFixed(0)}%</div>
                  </div>
                </div>

                <div className="dashboard-progress" style={{ marginTop: '12px' }}>
                  <div className="dashboard-progress-header">
                    <span>Concurrency ({runtime.concurrency.current}/{runtime.concurrency.max})</span>
                    <span>{((runtime.concurrency.current / Math.max(runtime.concurrency.max, 1)) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="dashboard-progress-bar">
                    <div
                      className="dashboard-progress-fill"
                      style={{
                        width: `${(runtime.concurrency.current / Math.max(runtime.concurrency.max, 1)) * 100}%`,
                        background: runtime.concurrency.current > runtime.concurrency.max * 0.8 ? '#f59e0b' : '#3b82f6',
                      }}
                    />
                  </div>
                </div>

                <div className="autopilot-card-actions">
                  {runtime.status === 'stopped' && (
                    <button className="btn-sm btn-success" onClick={() => handleStartAgent(runtime.agent_id, runtime.agent_name)}>
                      Start
                    </button>
                  )}
                  {(runtime.status === 'running' || runtime.status === 'idle') && (
                    <button className="btn-sm btn-danger" onClick={() => handleStopAgent(runtime.agent_id)}>
                      Stop
                    </button>
                  )}
                  <button className="btn-sm" onClick={() => handleRestartAgent(runtime.agent_id)}>
                    Restart
                  </button>
                </div>

                <div className="autopilot-card-time">
                  Started: {runtime.started_at ? new Date(runtime.started_at).toLocaleString() : 'N/A'}
                  {' · '}Restarts: {runtime.restart_count}
                  {' · '}Auto-restart: {runtime.auto_restart ? 'Yes' : 'No'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};