import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { SystemOverview, Agent } from '../types';

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

export default function Dashboard() {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [ov, ag] = await Promise.all([
        api.system.overview(),
        api.agents.list(),
      ]);
      setOverview(ov);
      setAgents(ag.items);
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, [loadData, refreshKey]);

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

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>System Dashboard</h1>
        <span className="dashboard-version">v{overview.version}</span>
        <button
          className="btn-secondary btn-sm"
          onClick={() => { setRefreshKey(k => k + 1); }}
        >
          Refresh
        </button>
      </div>

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

      {/* Agent List */}
      <div className="dashboard-section">
        <h3>Agents</h3>
        <div className="dashboard-agent-grid">
          {agents.map((agent) => (
            <div key={agent.id} className="dashboard-agent-card">
              <div className="dashboard-agent-avatar" style={{ background: '#3b82f6' }}>
                {agent.avatar}
              </div>
              <div className="dashboard-agent-info">
                <div className="dashboard-agent-name">{agent.name}</div>
                <div className="dashboard-agent-role">{agent.role}</div>
              </div>
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

      {/* MCP Servers */}
      <div className="dashboard-section">
        <h3>MCP Servers</h3>
        <div className="dashboard-stat-row">
          <span>Connected Servers</span>
          <strong>{overview.mcp_servers.total}</strong>
        </div>
      </div>
    </div>
  );
}