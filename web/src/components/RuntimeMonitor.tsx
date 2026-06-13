import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

interface RuntimeAgent {
  agent_id: string;
  agent_name: string;
  status: string;
  uptime_seconds: number;
  total_runtime: number;
  tasks_completed: number;
  tasks_failed: number;
  success_rate: number;
  restart_count: number;
  concurrency: { current: number; max: number };
  started_at: string;
  last_active: string;
  auto_restart: boolean;
}

interface DaemonStats {
  total_agents: number;
  active_agents: number;
  status_distribution: Record<string, number>;
  total_concurrency: number;
  max_total_concurrency: number;
  runtimes: RuntimeAgent[];
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  online: { label: 'Online', color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
  offline: { label: 'Offline', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.1)' },
  busy: { label: 'Busy', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
  idle: { label: 'Idle', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
  error: { label: 'Error', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' },
  running: { label: 'Running', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
  stopped: { label: 'Stopped', color: '#6b7280', bg: 'rgba(107, 114, 128, 0.1)' },
};

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ${mins % 60}m`;
  const days = Math.floor(hrs / 24);
  return `${days}d ${hrs % 24}h`;
}

function formatTokens(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

function computeHealthScore(agent: RuntimeAgent): number {
  let score = 50;
  // Success rate contributes up to 40 points
  score += agent.success_rate * 40;
  // Uptime bonus (up to 10 points for agents running > 1 hour)
  const uptimeBonus = Math.min(agent.uptime_seconds / 360, 10);
  score += uptimeBonus;
  return Math.min(100, Math.round(score));
}

function getHealthLabel(score: number): string {
  if (score >= 80) return 'Excellent';
  if (score >= 60) return 'Good';
  if (score >= 40) return 'Fair';
  return 'Poor';
}

function getHealthColor(score: number): string {
  if (score >= 80) return '#10b981';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

export const RuntimeMonitor: React.FC = () => {
  const [stats, setStats] = useState<DaemonStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());
  const [refreshInterval, setRefreshInterval] = useState(5000);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setError(null);
      const data = await api.daemon.stats();
      setStats(data as unknown as DaemonStats);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runtime stats');
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // WebSocket connection
  useEffect(() => {
    try {
      const ws = api.ws.connect();
      wsRef.current = ws;
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);
      return () => {
        ws.close();
        wsRef.current = null;
      };
    } catch {
      setWsConnected(false);
    }
  }, []);

  // Auto-refresh with configurable interval
  useEffect(() => {
    pollRef.current = setInterval(() => {
      fetchStats();
    }, refreshInterval);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchStats, refreshInterval]);

  const toggleCard = (agentId: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(agentId)) next.delete(agentId);
      else next.add(agentId);
      return next;
    });
  };

  const handleRestart = async (agentId: string) => {
    try {
      await api.daemon.restartAgent(agentId);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart agent');
    }
  };

  const handleStop = async (agentId: string) => {
    try {
      await api.daemon.stopAgent(agentId);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop agent');
    }
  };

  const handleStart = async (agentId: string) => {
    try {
      await api.daemon.startAgent(agentId);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start agent');
    }
  };

  const agents = stats?.runtimes || [];

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Runtime Monitor</h2>
          <p className="panel-subtitle">Agent runtime status and health</p>
        </div>
        <div className="panel-header-actions">
          <div className="runtime-ws-status" title={wsConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}>
            <span className={`runtime-ws-dot ${wsConnected ? 'connected' : 'disconnected'}`} />
            <span className="runtime-ws-label">{wsConnected ? 'Live' : 'Polling'}</span>
          </div>
          <div className="runtime-refresh-control">
            <label className="runtime-refresh-label">Refresh:</label>
            <select
              className="filter-select"
              value={refreshInterval}
              onChange={e => setRefreshInterval(Number(e.target.value))}
            >
              <option value={2000}>2s</option>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
              <option value={30000}>30s</option>
            </select>
          </div>
          <button className="btn-sm" onClick={fetchStats}>Refresh</button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="btn-sm" onClick={fetchStats}>Retry</button>
        </div>
      )}

      {/* Summary stats */}
      {stats && (
        <div className="runtime-summary-grid">
          <div className="runtime-summary-card">
            <span className="runtime-summary-value">{stats.total_agents}</span>
            <span className="runtime-summary-label">Total Agents</span>
          </div>
          <div className="runtime-summary-card">
            <span className="runtime-summary-value" style={{ color: '#10b981' }}>{stats.active_agents}</span>
            <span className="runtime-summary-label">Active</span>
          </div>
          <div className="runtime-summary-card">
            <span className="runtime-summary-value">{stats.total_concurrency}</span>
            <span className="runtime-summary-label">Concurrency</span>
          </div>
          <div className="runtime-summary-card">
            <span className="runtime-summary-value">{stats.max_total_concurrency}</span>
            <span className="runtime-summary-label">Max Concurrency</span>
          </div>
        </div>
      )}

      {loading && (
        <div className="panel-loading">Loading runtime data...</div>
      )}

      {!loading && agents.length === 0 && !error && (
        <div className="panel-empty runtime-empty">
          <div className="runtime-empty-icon">🖧</div>
          <p>No agent runtimes available</p>
          <span>Start agents from the Daemon panel to see their runtime status here.</span>
        </div>
      )}

      {/* Agent Cards */}
      <div className="runtime-agent-grid">
        {agents.map(agent => {
          const statusConfig = STATUS_CONFIG[agent.status] || STATUS_CONFIG.offline;
          const healthScore = computeHealthScore(agent);
          const healthColor = getHealthColor(healthScore);
          const isExpanded = expandedCards.has(agent.agent_id);
          const successRate = Math.round(agent.success_rate * 100);

          return (
            <div key={agent.agent_id} className={`runtime-agent-card ${isExpanded ? 'expanded' : ''}`}>
              <div className="runtime-agent-header" onClick={() => toggleCard(agent.agent_id)}>
                <div className="runtime-agent-avatar" style={{ background: healthColor }}>
                  {agent.agent_name.charAt(0).toUpperCase()}
                </div>
                <div className="runtime-agent-info">
                  <div className="runtime-agent-name">{agent.agent_name}</div>
                  <div className="runtime-agent-id">{agent.agent_id}</div>
                </div>
                <span
                  className="runtime-status-badge"
                  style={{ background: statusConfig.bg, color: statusConfig.color }}
                >
                  {statusConfig.label}
                </span>
                <span className="runtime-agent-expand">{isExpanded ? '▾' : '▸'}</span>
              </div>

              {/* Compact gauges */}
              <div className="runtime-gauges">
                <div className="runtime-gauge">
                  <div className="runtime-gauge-header">
                    <span className="runtime-gauge-label">Health</span>
                    <span className="runtime-gauge-value" style={{ color: healthColor }}>{healthScore}</span>
                  </div>
                  <div className="runtime-gauge-track">
                    <div
                      className="runtime-gauge-fill"
                      style={{ width: `${healthScore}%`, background: healthColor }}
                    />
                  </div>
                </div>
                <div className="runtime-gauge">
                  <div className="runtime-gauge-header">
                    <span className="runtime-gauge-label">Success Rate</span>
                    <span className="runtime-gauge-value">{successRate}%</span>
                  </div>
                  <div className="runtime-gauge-track">
                    <div
                      className="runtime-gauge-fill"
                      style={{ width: `${successRate}%`, background: successRate >= 80 ? '#10b981' : successRate >= 50 ? '#f59e0b' : '#ef4444' }}
                    />
                  </div>
                </div>
                <div className="runtime-gauge">
                  <div className="runtime-gauge-header">
                    <span className="runtime-gauge-label">Concurrency</span>
                    <span className="runtime-gauge-value">{agent.concurrency.current}/{agent.concurrency.max}</span>
                  </div>
                  <div className="runtime-gauge-track">
                    <div
                      className="runtime-gauge-fill"
                      style={{ width: `${agent.concurrency.max > 0 ? (agent.concurrency.current / agent.concurrency.max) * 100 : 0}%`, background: '#3b82f6' }}
                    />
                  </div>
                </div>
              </div>

              {/* Quick stats bar */}
              <div className="runtime-quick-stats">
                <div className="runtime-quick-stat">
                  <span className="runtime-quick-stat-value">{formatUptime(agent.uptime_seconds)}</span>
                  <span className="runtime-quick-stat-label">Uptime</span>
                </div>
                <div className="runtime-quick-stat">
                  <span className="runtime-quick-stat-value">{agent.tasks_completed}</span>
                  <span className="runtime-quick-stat-label">Completed</span>
                </div>
                <div className="runtime-quick-stat">
                  <span className="runtime-quick-stat-value" style={{ color: agent.tasks_failed > 0 ? '#ef4444' : undefined }}>
                    {agent.tasks_failed}
                  </span>
                  <span className="runtime-quick-stat-label">Failed</span>
                </div>
                <div className="runtime-quick-stat">
                  <span className="runtime-quick-stat-value">{agent.restart_count}</span>
                  <span className="runtime-quick-stat-label">Restarts</span>
                </div>
              </div>

              {/* Quick actions */}
              <div className="runtime-agent-actions">
                {agent.status === 'stopped' || agent.status === 'offline' ? (
                  <button className="btn-sm btn-success" onClick={() => handleStart(agent.agent_id)}>Start</button>
                ) : (
                  <button className="btn-sm btn-danger" onClick={() => handleStop(agent.agent_id)}>Stop</button>
                )}
                <button className="btn-sm" onClick={() => handleRestart(agent.agent_id)}>Restart</button>
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div className="runtime-agent-details">
                  <div className="runtime-detail-grid">
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Status</span>
                      <span className="runtime-detail-value" style={{ color: statusConfig.color }}>{statusConfig.label}</span>
                    </div>
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Health Score</span>
                      <span className="runtime-detail-value" style={{ color: healthColor }}>{healthScore} — {getHealthLabel(healthScore)}</span>
                    </div>
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Uptime</span>
                      <span className="runtime-detail-value">{formatUptime(agent.uptime_seconds)}</span>
                    </div>
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Total Runtime</span>
                      <span className="runtime-detail-value">{formatUptime(agent.total_runtime)}</span>
                    </div>
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Started At</span>
                      <span className="runtime-detail-value">{agent.started_at ? new Date(agent.started_at).toLocaleString() : 'N/A'}</span>
                    </div>
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Last Active</span>
                      <span className="runtime-detail-value">{agent.last_active ? new Date(agent.last_active).toLocaleString() : 'N/A'}</span>
                    </div>
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Auto Restart</span>
                      <span className="runtime-detail-value">{agent.auto_restart ? 'Enabled' : 'Disabled'}</span>
                    </div>
                    <div className="runtime-detail-item">
                      <span className="runtime-detail-label">Success Rate</span>
                      <span className="runtime-detail-value">{successRate}%</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RuntimeMonitor;