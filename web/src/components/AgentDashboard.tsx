import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

interface AgentDashboardEntry {
  id: string;
  name: string;
  role: string;
  personality: string;
  avatar: string;
  is_active: boolean;
  created_at: string;
  tasks: { total: number; by_status: Record<string, number> };
  memory: { total: number };
  dream: { is_running: boolean; interval_seconds: number; total_insights: number };
  iteration: { remaining: number; is_exhausted: boolean; usage_ratio: number; total_tokens: number };
  tools: { total_executions: number; successful: number; failed: number };
  costs: { total_cost: number; total_tokens: number };
}

interface DashboardData {
  agents: AgentDashboardEntry[];
  total_agents: number;
  system_summary: {
    total_tasks: number;
    total_memories: number;
    active_dream_engines: number;
    total_tokens_used: number;
  };
}

const STATUS_COLORS: Record<string, string> = {
  completed: '#10b981',
  running: '#3b82f6',
  failed: '#ef4444',
  cancelled: '#9ca3af',
  queued: '#f59e0b',
  dispatched: '#8b5cf6',
};

const ROLE_COLORS: Record<string, string> = {
  strategy: '#6366f1',
  engineering: '#06b6d4',
  research: '#f59e0b',
  companion: '#ec4899',
  design: '#8b5cf6',
  writing: '#10b981',
  custom: '#6b7280',
};

export const AgentDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const refreshTimerRef = useRef<number | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const result = await api.agentDashboard.overview();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    refreshTimerRef.current = window.setInterval(fetchDashboard, 10000);
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
  }, [autoRefresh, fetchDashboard]);

  // WebSocket for real-time events
  useEffect(() => {
    const connectWs = () => {
      try {
        const ws = api.ws.connect();
        wsRef.current = ws;
        ws.onopen = () => {
          ws.send(JSON.stringify({ action: 'subscribe', room: 'system' }));
        };
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (['agent_status', 'task_update', 'dream_update'].includes(msg.type)) {
              fetchDashboard();
            }
          } catch {}
        };
        ws.onclose = () => setTimeout(connectWs, 5000);
        ws.onerror = () => ws.close();
      } catch {
        setTimeout(connectWs, 5000);
      }
    };
    connectWs();
    return () => { wsRef.current?.close(); };
  }, [fetchDashboard]);

  const formatUptime = (createdAt: string) => {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - created.getTime();
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    return days > 0 ? `${days}d` : 'Today';
  };

  if (loading) {
    return (
      <div className="panel-loading">
        <div className="spinner" />
        <span>Loading agent dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-error">
        <span>{error}</span>
        <button className="btn-secondary" onClick={fetchDashboard}>Retry</button>
      </div>
    );
  }

  if (!data || data.agents.length === 0) {
    return (
      <div className="panel-empty">
        <div className="empty-icon">B</div>
        <h3>No Active Agents</h3>
        <p>Create your first agent to see the dashboard.</p>
      </div>
    );
  }

  return (
    <div className="panel agent-dashboard">
      <div className="panel-header">
        <h2>Agent Dashboard</h2>
        <div className="panel-header-actions">
          <button
            className={`btn-sm ${autoRefresh ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
          <button className="btn-sm btn-secondary" onClick={fetchDashboard}>
            Refresh
          </button>
        </div>
      </div>

      {/* System Summary Bar */}
      <div className="dashboard-summary">
        <div className="summary-card">
          <div className="summary-value">{data.total_agents}</div>
          <div className="summary-label">Agents</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">{data.system_summary.total_tasks}</div>
          <div className="summary-label">Tasks</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">{data.system_summary.total_memories}</div>
          <div className="summary-label">Memories</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">{data.system_summary.active_dream_engines}</div>
          <div className="summary-label">Dreams Active</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">{data.system_summary.total_tokens_used.toLocaleString()}</div>
          <div className="summary-label">Tokens Used</div>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="dashboard-agents">
        {data.agents.map((agent) => {
          const isExpanded = expandedAgent === agent.id;
          const roleColor = ROLE_COLORS[agent.role] || '#6b7280';
          const completedTasks = agent.tasks.by_status['completed'] || 0;
          const runningTasks = agent.tasks.by_status['running'] || 0;
          const failedTasks = agent.tasks.by_status['failed'] || 0;
          const successRate = agent.tools.total_executions > 0
            ? Math.round((agent.tools.successful / agent.tools.total_executions) * 100)
            : null;

          return (
            <div
              key={agent.id}
              className={`agent-card ${isExpanded ? 'expanded' : ''}`}
              onClick={() => setExpandedAgent(isExpanded ? null : agent.id)}
            >
              <div className="agent-card-header" style={{ borderLeftColor: roleColor }}>
                <div className="agent-avatar" style={{ background: roleColor }}>
                  {agent.avatar || agent.name[0]}
                </div>
                <div className="agent-card-info">
                  <h3 className="agent-card-name">{agent.name}</h3>
                  <span className="agent-card-role" style={{ color: roleColor }}>
                    {agent.role}
                  </span>
                </div>
                <div className="agent-card-stats-compact">
                  <div className="stat-mini">
                    <span className="stat-value">{agent.tasks.total}</span>
                    <span className="stat-label">Tasks</span>
                  </div>
                  <div className="stat-mini">
                    <span className="stat-value">{agent.memory.total}</span>
                    <span className="stat-label">Mem</span>
                  </div>
                  <div className={`status-indicator ${agent.dream.is_running ? 'active' : 'idle'}`}
                    title={agent.dream.is_running ? 'Dream engine active' : 'Dream engine idle'}
                  />
                </div>
              </div>

              {/* Progress bars */}
              <div className="agent-card-bars">
                {/* Task status distribution */}
                {agent.tasks.total > 0 && (
                  <div className="progress-stacked">
                    {Object.entries(agent.tasks.by_status).map(([status, count]) => {
                      const pct = (count / agent.tasks.total) * 100;
                      return pct > 0 ? (
                        <div
                          key={status}
                          className="progress-segment"
                          style={{
                            width: `${pct}%`,
                            background: STATUS_COLORS[status] || '#9ca3af',
                          }}
                          title={`${status}: ${count}`}
                        />
                      ) : null;
                    })}
                  </div>
                )}

                {/* Iteration budget bar */}
                <div className="progress-bar-container">
                  <div className="progress-label">Budget</div>
                  <div className="progress-bar-track">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${Math.max(0, 100 - agent.iteration.usage_ratio * 100)}%`,
                        background: agent.iteration.is_exhausted ? '#ef4444' : '#3b82f6',
                      }}
                    />
                  </div>
                  <div className="progress-value">{agent.iteration.remaining}</div>
                </div>
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div className="agent-card-details">
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">Personality</span>
                      <span className="detail-value">{agent.personality}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Created</span>
                      <span className="detail-value">{formatUptime(agent.created_at)}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Tokens Used</span>
                      <span className="detail-value">{agent.iteration.total_tokens.toLocaleString()}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Cost</span>
                      <span className="detail-value">${agent.costs.total_cost.toFixed(4)}</span>
                    </div>
                    {successRate !== null && (
                      <div className="detail-item">
                        <span className="detail-label">Tool Success Rate</span>
                        <span className="detail-value" style={{
                          color: successRate > 80 ? '#10b981' : successRate > 50 ? '#f59e0b' : '#ef4444',
                        }}>
                          {successRate}%
                        </span>
                      </div>
                    )}
                    <div className="detail-item">
                      <span className="detail-label">Dream Engine</span>
                      <span className="detail-value">
                        {agent.dream.is_running
                          ? `Active (${agent.dream.interval_seconds}s)`
                          : 'Idle'}
                        {agent.dream.total_insights > 0 && ` - ${agent.dream.total_insights} insights`}
                      </span>
                    </div>
                  </div>

                  {/* Task breakdown */}
                  {agent.tasks.total > 0 && (
                    <div className="task-breakdown">
                      <div className="section-label">Task Status</div>
                      <div className="task-status-grid">
                        {Object.entries(agent.tasks.by_status).map(([status, count]) => (
                          <div key={status} className="task-status-item">
                            <span
                              className="status-dot"
                              style={{ background: STATUS_COLORS[status] || '#9ca3af' }}
                            />
                            <span className="status-name">{status}</span>
                            <span className="status-count">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};