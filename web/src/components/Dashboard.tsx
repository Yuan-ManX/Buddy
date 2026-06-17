import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { SystemOverview, Agent, SystemHealthStatus, TokenUsageData, AgentState, ActivityFeedEntry } from '../types';
import { useTheme } from '../hooks/useTheme';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon: string;
  color: string;
}

function MetricCard({ label, value, subtext, icon, color }: MetricCardProps) {
  return (
    <div className="dashboard-card">
      <div className="dashboard-card-icon" style={{ background: color }}>
        {icon}
      </div>
      <div className="dashboard-card-body">
        <div className="dashboard-card-value">{value}</div>
        <div className="dashboard-card-label">{label}</div>
        {subtext && <div className="dashboard-card-subtext">{subtext}</div>}
      </div>
    </div>
  );
}

interface ProgressBarProps {
  label: string;
  current: number;
  total: number;
  color: string;
}

function ProgressBar({ label, current, total, color }: ProgressBarProps) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className="dashboard-progress">
      <div className="dashboard-progress-header">
        <span>{label}</span>
        <span>{current}/{total} ({pct}%)</span>
      </div>
      <div className="dashboard-progress-bar">
        <div
          className="dashboard-progress-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

// Health score gauge component
function HealthGauge({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = clamped >= 70 ? '#22c55e' : clamped >= 40 ? '#f59e0b' : '#ef4444';
  const label = clamped >= 70 ? 'Healthy' : clamped >= 40 ? 'Degraded' : 'Critical';
  const circumference = 2 * Math.PI * 36;
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div className="health-gauge">
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle
          cx="50" cy="50" r="36"
          fill="none"
          stroke="var(--border)"
          strokeWidth="8"
        />
        <circle
          cx="50" cy="50" r="36"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        <text x="50" y="46" textAnchor="middle" className="health-gauge-value" fill={color}>
          {clamped}
        </text>
        <text x="50" y="62" textAnchor="middle" className="health-gauge-label">
          {label}
        </text>
      </svg>
    </div>
  );
}

// Sparkline for agent activity
function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length === 0) return <div className="sparkline-empty">No data</div>;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const width = 80;
  const height = 24;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1 || 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="sparkline">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

// WS connection status
function WSStatus({ connected }: { connected: boolean }) {
  return (
    <div className={`ws-status-indicator ${connected ? 'connected' : 'disconnected'}`}>
      <span className="ws-status-dot" />
      <span className="ws-status-text">{connected ? 'Connected' : 'Disconnected'}</span>
    </div>
  );
}

export default function Dashboard() {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [platformHealth, setPlatformHealth] = useState<any>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [healthScore, setHealthScore] = useState(75);
  const [activityData, setActivityData] = useState<Record<string, number[]>>({});
  const [refreshInterval, setRefreshInterval] = useState(15);
  const [alerts, setAlerts] = useState<Array<{ id: string; type: string; message: string; time: string; severity: string }>>([]);
  const { mode, toggle: toggleTheme, isDark } = useTheme();
  const wsRef = useRef<WebSocket | null>(null);

  // Token usage state
  const [tokenUsageData, setTokenUsageData] = useState<TokenUsageData | null>(null);
  const [tokenUsageChart, setTokenUsageChart] = useState<Array<{ hour: number; tokens: number }>>([]);

  // Active agents state
  const [activeAgents, setActiveAgents] = useState<AgentState[]>([]);

  // Recent activity state
  const [recentActivities, setRecentActivities] = useState<ActivityFeedEntry[]>([]);

  // Dashboard sections
  const [activeSection, setActiveSection] = useState<'overview' | 'token-usage' | 'active-agents' | 'recent-activity'>('overview');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [ov, ag, ph] = await Promise.all([
        api.system.overview(),
        api.agents.list(),
        api.platformHub.health().catch(() => null),
      ]);
      setOverview(ov);
      setAgents(ag.items);
      setPlatformHealth(ph);

      // Calculate health score
      if (ph) {
        const subsystemsRunning = ph.subsystem_count?.running || 0;
        const subsystemsTotal = ph.subsystem_count?.total || 1;
        const ratio = ph.health_ratio ?? (subsystemsRunning / subsystemsTotal);
        setHealthScore(Math.round(ratio * 100));
      }

      // Load guard alerts
      try {
        const guardAlerts = await api.guard.alerts(undefined, 'warning');
        if (guardAlerts && Array.isArray(guardAlerts)) {
          setAlerts(guardAlerts.slice(0, 10).map((a: any, i: number) => ({
            id: a.id || `alert-${i}`,
            type: a.type || a.alert_type || 'system',
            message: a.message || a.description || JSON.stringify(a),
            time: a.timestamp || a.created_at || new Date().toISOString(),
            severity: a.severity || 'warning',
          })));
        }
      } catch {
        // alerts are optional
      }
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTokenUsage = async () => {
    try {
      const data = await api.system.tokenUsage();
      setTokenUsageData(data);
      if (data.daily && data.daily.length > 0) {
        setTokenUsageChart(data.daily.map((d) => {
          const hour = new Date(d.date).getHours();
          return { hour, tokens: d.tokens };
        }));
      }
    } catch {
      // token usage is optional
    }
  };

  const loadActiveAgents = async () => {
    try {
      const result = await api.system.activeAgents();
      setActiveAgents(result.agents);
    } catch {
      // active agents is optional
    }
  };

  const loadRecentActivity = async () => {
    try {
      const result = await api.system.recentActivity(30);
      setRecentActivities(result.activities);
    } catch {
      // recent activity is optional
    }
  };

  // WebSocket connection for real-time status
  useEffect(() => {
    try {
      const ws = api.ws.connect();
      wsRef.current = ws;
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'agent_activity' && data.agent_id) {
            setActivityData((prev) => {
              const existing = prev[data.agent_id] || Array(10).fill(0);
              const updated = [...existing.slice(1), data.count || 1];
              return { ...prev, [data.agent_id]: updated };
            });
          }
          if (data.type === 'system_health_update') {
            setPlatformHealth((prev: any) => ({ ...prev, ...data.payload }));
            if (data.payload?.health_ratio !== undefined) {
              setHealthScore(Math.round(data.payload.health_ratio * 100));
            }
          }
          if (data.type === 'token_usage_update' && data.payload) {
            setTokenUsageChart((prev) => {
              const hour = new Date().getHours();
              const updated = [...prev];
              const existing = updated.find((h) => h.hour === hour);
              if (existing) {
                existing.tokens = data.payload.tokens || existing.tokens;
              } else {
                updated.push({ hour, tokens: data.payload.tokens || 0 });
              }
              return updated.slice(-24);
            });
          }
          if (data.type === 'activity_update' && data.payload) {
            setRecentActivities((prev) => [data.payload, ...prev].slice(0, 30));
          }
        } catch {}
      };

      return () => {
        ws.close();
        wsRef.current = null;
      };
    } catch {
      setWsConnected(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, refreshInterval * 1000);
    return () => clearInterval(interval);
  }, [loadData, refreshKey, refreshInterval]);

  // Initialize some activity data for agents
  useEffect(() => {
    if (agents.length > 0 && Object.keys(activityData).length === 0) {
      const seed: Record<string, number[]> = {};
      agents.forEach((a) => {
        seed[a.id] = Array.from({ length: 10 }, () => Math.floor(Math.random() * 10));
      });
      setActivityData(seed);
    }
  }, [agents]);

  if (loading && !overview) {
    return (
      <div className="dashboard-loading">
        <div className="dashboard-spinner" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="dashboard-empty">
        <p>Unable to load system data. Is the backend running?</p>
      </div>
    );
  }

  const tierColors: Record<string, string> = {
    light: '#22c55e',
    standard: '#3b82f6',
    premium: '#8b5cf6',
  };

  const totalTokens = overview.costs.total_tokens;
  const tasksCompletedToday = overview.tasks.total - (overview.tasks.active || 0);

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>System Dashboard</h1>
        <span className="dashboard-version">v{overview.version}</span>
        <WSStatus connected={wsConnected} />
        <button
          className="btn-secondary btn-sm"
          onClick={() => { setRefreshKey(k => k + 1); }}
        >
          Refresh
        </button>
        <button
          className="sidebar-theme-toggle"
          onClick={toggleTheme}
          title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
        >
          {isDark ? '☀️' : '🌙'}
        </button>
        <select
          className="dashboard-refresh-select"
          value={refreshInterval}
          onChange={(e) => setRefreshInterval(Number(e.target.value))}
          title="Auto-refresh interval"
        >
          <option value={5}>5s</option>
          <option value={15}>15s</option>
          <option value={30}>30s</option>
          <option value={60}>60s</option>
        </select>
      </div>

      {/* Health Score & Quick Stats Row */}
      <div className="dashboard-top-row">
        <div className="dashboard-section dashboard-health-section">
          <h3>System Health</h3>
          <HealthGauge score={healthScore} />
        </div>
        <div className="dashboard-section dashboard-quick-stats">
          <h3>Quick Stats</h3>
          <div className="quick-stats-grid">
            <div className="quick-stat-item">
              <span className="quick-stat-value">{totalTokens.toLocaleString()}</span>
              <span className="quick-stat-label">Total Tokens</span>
            </div>
            <div className="quick-stat-item">
              <span className="quick-stat-value">{overview.agents.active}</span>
              <span className="quick-stat-label">Active Sessions</span>
            </div>
            <div className="quick-stat-item">
              <span className="quick-stat-value">{tasksCompletedToday}</span>
              <span className="quick-stat-label">Tasks Completed</span>
            </div>
            <div className="quick-stat-item">
              <span className="quick-stat-value">{overview.conversations.total}</span>
              <span className="quick-stat-label">Conversations</span>
            </div>
          </div>
        </div>
      </div>

      {/* System Alerts */}
      {alerts.length > 0 && (
        <div className="dashboard-section dashboard-alerts">
          <h3>System Alerts</h3>
          <div className="alerts-list">
            {alerts.map((alert) => (
              <div key={alert.id} className={`alert-item alert-${alert.severity}`}>
                <span className={`alert-severity-dot severity-${alert.severity}`} />
                <div className="alert-content">
                  <span className="alert-type">{alert.type}</span>
                  <span className="alert-message">{alert.message}</span>
                </div>
                <span className="alert-time">{new Date(alert.time).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div className="dashboard-metrics">
        <MetricCard
          label="Active Agents"
          value={`${overview.agents.active} / ${overview.agents.total}`}
          icon="A"
          color="#3b82f6"
        />
        <MetricCard
          label="Tasks"
          value={`${overview.tasks.active} active`}
          subtext={`${overview.tasks.total} total`}
          icon="T"
          color="#f59e0b"
        />
        <MetricCard
          label="Conversations"
          value={overview.conversations.total}
          icon="C"
          color="#22c55e"
        />
        <MetricCard
          label="Memories"
          value={overview.memories.total}
          icon="M"
          color="#8b5cf6"
        />
        <MetricCard
          label="Autopilots"
          value={overview.autopilots.total}
          icon="P"
          color="#ef4444"
        />
        <MetricCard
          label="Plans"
          value={overview.plans.total}
          icon="PL"
          color="#06b6d4"
        />
        <MetricCard
          label="Templates"
          value={overview.templates.total}
          icon="W"
          color="#14b8a6"
        />
        <MetricCard
          label="Est. Monthly Cost"
          value={`$${overview.costs.estimated_monthly.toFixed(4)}`}
          subtext={`${overview.costs.total_tokens.toLocaleString()} tokens`}
          icon="$"
          color="#6366f1"
        />
      </div>

      {/* Agent List with Sparklines */}
      <div className="dashboard-section">
        <h3>Agents & Activity</h3>
        <div className="dashboard-agent-grid-activity">
          {agents.map((agent) => (
            <div key={agent.id} className="dashboard-agent-card-activity">
              <div className="dashboard-agent-avatar" style={{ background: '#3b82f6' }}>
                {agent.avatar}
              </div>
              <div className="dashboard-agent-info">
                <div className="dashboard-agent-name">{agent.name}</div>
                <div className="dashboard-agent-role">{agent.role}</div>
              </div>
              <Sparkline data={activityData[agent.id] || []} color="#3b82f6" />
              <span className={`dashboard-badge ${agent.is_active ? 'active' : 'inactive'}`}>
                {agent.is_active ? 'active' : 'inactive'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Routing Stats */}
      <div className="dashboard-section">
        <h3>Model Routing</h3>
        <div className="dashboard-routing-stats">
          <div className="dashboard-stat-row">
            <span>Total Requests</span>
            <strong>{overview.routing.total_requests}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Avg Cost</span>
            <strong>{overview.routing.average_cost}</strong>
          </div>
          {Object.entries(overview.routing.tier_distribution).map(([tier, count]) => (
            <div key={tier} className="dashboard-stat-row">
              <span>
                <span
                  className="dashboard-tier-dot"
                  style={{ background: tierColors[tier] || '#94a3b8' }}
                />
                {tier}
              </span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </div>

      {/* Tool Stats */}
      <div className="dashboard-section">
        <h3>Tool Execution</h3>
        <ProgressBar
          label="Success Rate"
          current={overview.tools.successful}
          total={overview.tools.total_executions}
          color="#22c55e"
        />
        <div className="dashboard-stat-row">
          <span>Total Executions</span>
          <strong>{overview.tools.total_executions}</strong>
        </div>
        <div className="dashboard-stat-row">
          <span>Failed</span>
          <strong style={{ color: '#ef4444' }}>{overview.tools.failed}</strong>
        </div>
      </div>

      {/* Orchestrator Stats */}
      <div className="dashboard-section">
        <h3>Orchestrator</h3>
        <div className="dashboard-stat-row">
          <span>Active Agents</span>
          <strong>{overview.orchestrator.active_agents}</strong>
        </div>
        <div className="dashboard-stat-row">
          <span>Trust Relationships</span>
          <strong>{overview.orchestrator.trust_relationships}</strong>
        </div>
        <div className="dashboard-stat-row">
          <span>Collaboration Threads</span>
          <strong>{overview.orchestrator.collaboration_threads}</strong>
        </div>
      </div>

      {/* Trajectory Stats */}
      <div className="dashboard-section">
        <h3>Trajectory & Compression</h3>
        <div className="dashboard-stat-row">
          <span>Trajectories Compressed</span>
          <strong>{overview.trajectory.total_compressed}</strong>
        </div>
        <div className="dashboard-stat-row">
          <span>Success Rate</span>
          <strong>{overview.trajectory.success_rate ? `${(overview.trajectory.success_rate * 100).toFixed(1)}%` : 'N/A'}</strong>
        </div>
        <div className="dashboard-stat-row">
          <span>Avg Quality Score</span>
          <strong>{overview.trajectory.avg_quality_score ? overview.trajectory.avg_quality_score.toFixed(2) : 'N/A'}</strong>
        </div>
      </div>

      {/* Compressor Stats */}
      {overview.compressor && overview.compressor.total_trajectories_compressed > 0 && (
        <div className="dashboard-section">
          <h3>Execution Patterns</h3>
          <div className="dashboard-stat-row">
            <span>Patterns Detected</span>
            <strong>{overview.compressor.total_patterns_detected}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Avg Compression Ratio</span>
            <strong>{overview.compressor.average_compression_ratio ? `${overview.compressor.average_compression_ratio.toFixed(1)}x` : 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Bytes Saved</span>
            <strong>{overview.compressor.total_bytes_saved ? `${(overview.compressor.total_bytes_saved / 1024).toFixed(1)} KB` : 'N/A'}</strong>
          </div>
          {Object.entries(overview.compressor.patterns_by_type || {}).map(([type, count]) => (
            <div key={type} className="dashboard-stat-row">
              <span style={{ textTransform: 'capitalize' }}>{type.replace(/_/g, ' ')}</span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      )}

      {/* MCP Servers */}
      <div className="dashboard-section">
        <h3>MCP Servers</h3>
        <div className="dashboard-stat-row">
          <span>Connected Servers</span>
          <strong>{overview.mcp_servers.total}</strong>
        </div>
      </div>

      {/* Platform Health */}
      {platformHealth && (
        <div className="dashboard-section">
          <h3>Platform Health</h3>
          <div className="dashboard-stat-row">
            <span>Overall Status</span>
            <strong>
              <span
                className="dashboard-tier-dot"
                style={{
                  background:
                    platformHealth.overall === 'healthy' ? '#22c55e' :
                    platformHealth.overall === 'degraded' ? '#f59e0b' :
                    '#ef4444',
                }}
              />
              {platformHealth.overall}
            </strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Uptime</span>
            <strong>{platformHealth.uptime_seconds < 60
              ? `${Math.round(platformHealth.uptime_seconds)}s`
              : platformHealth.uptime_seconds < 3600
              ? `${Math.round(platformHealth.uptime_seconds / 60)}m`
              : `${Math.round(platformHealth.uptime_seconds / 3600)}h`
            }</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Subsystems Running</span>
            <strong>{platformHealth.subsystem_count?.running || 0}/{platformHealth.subsystem_count?.total || 0}</strong>
          </div>
          {platformHealth.health_ratio !== undefined && (
            <ProgressBar
              label="Health Ratio"
              current={Math.round(platformHealth.health_ratio * 100)}
              total={100}
              color={platformHealth.health_ratio >= 1 ? '#22c55e' : platformHealth.health_ratio >= 0.7 ? '#f59e0b' : '#ef4444'}
            />
          )}
        </div>
      )}

      {/* Token Usage Chart */}
      <div className="dashboard-section">
        <div className="dashboard-section-header">
          <h3>Token Usage (Last 24 Hours)</h3>
          <button className="btn btn-sm btn-secondary" onClick={loadTokenUsage}>Load</button>
        </div>
        {tokenUsageChart.length > 0 ? (
          <>
            <div className="chart-container">
              <div className="chart-bars">
                {tokenUsageChart.map((hour, i) => {
                  const maxTokens = Math.max(...tokenUsageChart.map((h) => h.tokens), 1);
                  return (
                    <div key={i} className="chart-bar">
                      <div
                        className="bar-fill"
                        style={{ height: `${Math.min(100, (hour.tokens / maxTokens) * 100)}%` }}
                      />
                      <div className="bar-label">{hour.hour}:00</div>
                    </div>
                  );
                })}
              </div>
            </div>
            {tokenUsageData && (
              <div className="token-metrics">
                <div className="metric-item">
                  <span className="metric-label">Monthly Total</span>
                  <span className="metric-value">{tokenUsageData.monthly_total.toLocaleString()} tokens</span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">Monthly Cost</span>
                  <span className="metric-value">${tokenUsageData.monthly_cost.toFixed(4)}</span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">Projected Cost</span>
                  <span className="metric-value">${tokenUsageData.projected_cost.toFixed(2)}</span>
                </div>
              </div>
            )}
            {tokenUsageData && tokenUsageData.by_model && Object.keys(tokenUsageData.by_model).length > 0 && (
              <div className="model-breakdown">
                <h4>By Model</h4>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(tokenUsageData.by_model).map(([model, data]) => (
                        <tr key={model}>
                          <td>{model}</td>
                          <td>{data.tokens.toLocaleString()}</td>
                          <td>${data.cost.toFixed(6)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="empty-state">No token usage data available.</p>
        )}
      </div>

      {/* Active Agents */}
      <div className="dashboard-section">
        <div className="dashboard-section-header">
          <h3>Active Agents</h3>
          <button className="btn btn-sm btn-secondary" onClick={loadActiveAgents}>Load</button>
        </div>
        {activeAgents.length > 0 ? (
          <div className="active-agents-list">
            {activeAgents.map((a) => (
              <div key={a.agent_id} className="active-agent-card">
                <div className="active-agent-header">
                  <span className="active-agent-name">{a.agent_name}</span>
                  <span className={`badge ${a.state === 'running' ? 'badge-success' : a.state === 'idle' ? 'badge-warning' : 'badge-error'}`}>
                    {a.state}
                  </span>
                </div>
                {a.current_task && (
                  <div className="active-agent-task">
                    <span className="task-label">Current Task:</span>
                    <span className="task-value truncate">{a.current_task}</span>
                  </div>
                )}
                <div className="active-agent-meta">
                  <span>Uptime: {a.uptime_seconds < 60 ? `${a.uptime_seconds}s` : a.uptime_seconds < 3600 ? `${Math.round(a.uptime_seconds / 60)}m` : `${Math.round(a.uptime_seconds / 3600)}h`}</span>
                  <span>Last Active: {new Date(a.last_active).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">No active agent data available.</p>
        )}
      </div>

      {/* Recent Activity */}
      <div className="dashboard-section">
        <div className="dashboard-section-header">
          <h3>Recent Activity</h3>
          <button className="btn btn-sm btn-secondary" onClick={loadRecentActivity}>Load</button>
        </div>
        {recentActivities.length > 0 ? (
          <div className="activity-feed">
            {recentActivities.map((activity) => (
              <div key={activity.id} className="activity-entry">
                <div className="activity-dot" />
                <div className="activity-content">
                  <div className="activity-header">
                    <span className="activity-agent">{activity.agent_name || activity.agent_id}</span>
                    <span className="badge badge-sm">{activity.type}</span>
                  </div>
                  <p className="activity-description">{activity.description}</p>
                  <span className="activity-time">{new Date(activity.timestamp).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">No recent activity data available.</p>
        )}
      </div>
    </div>
  );
}