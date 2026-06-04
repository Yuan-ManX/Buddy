import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

interface SystemOverview {
  service: string;
  version: string;
  agents: { total: number; active: number };
  tasks: { total: number; active: number };
  conversations: { total: number };
  memories: { total: number };
  autopilots: { total: number };
  plans: { total: number };
  mcp_servers: { total: number };
  routing: { total_requests: number; tier_distribution: Record<string, number>; average_cost: string };
  tools: { total_executions: number; successful: number; failed: number; success_rate: string };
  orchestrator: { active_agents: number; trust_relationships: number; collaboration_threads: number };
}

export const SystemOverview: React.FC = () => {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadOverview();
    const interval = setInterval(loadOverview, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadOverview = async () => {
    try {
      const data = await api.system.overview();
      setOverview(data);
      setError('');
    } catch (e: any) {
      setError(e.message || 'Failed to load system overview');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="overview-panel">
        <div className="loading">Loading system overview...</div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="overview-panel">
        <div className="error-banner">{error || 'No data available'}</div>
      </div>
    );
  }

  const cards = [
    { label: 'Agents', value: overview.agents.total, sub: `${overview.agents.active} active`, color: '#3b82f6', icon: '🤖' },
    { label: 'Tasks', value: overview.tasks.total, sub: `${overview.tasks.active} active`, color: '#f59e0b', icon: '📋' },
    { label: 'Conversations', value: overview.conversations.total, sub: '', color: '#10b981', icon: '💬' },
    { label: 'Memories', value: overview.memories.total, sub: '', color: '#8b5cf6', icon: '🧠' },
    { label: 'Autopilots', value: overview.autopilots.total, sub: '', color: '#ec4899', icon: '🔄' },
    { label: 'Plans', value: overview.plans.total, sub: '', color: '#06b6d4', icon: '📐' },
    { label: 'MCP Servers', value: overview.mcp_servers.total, sub: '', color: '#f97316', icon: '🔌' },
    { label: 'Tool Executions', value: overview.tools.total_executions, sub: overview.tools.success_rate, color: '#84cc16', icon: '🔧' },
  ];

  return (
    <div className="overview-panel">
      <h2>System Overview</h2>
      <p className="subtitle">{overview.service} v{overview.version} — Real-time platform status</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="card-grid">
        {cards.map(card => (
          <div key={card.label} className="stat-card" style={{ borderTop: `3px solid ${card.color}` }}>
            <div className="card-icon">{card.icon}</div>
            <div className="card-content">
              <span className="card-value">{card.value}</span>
              <span className="card-label">{card.label}</span>
              {card.sub && <span className="card-sub">{card.sub}</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="detail-grid">
        <div className="detail-section">
          <h3>Routing</h3>
          <div className="detail-row">
            <span>Total Requests</span>
            <span>{overview.routing.total_requests}</span>
          </div>
          <div className="detail-row">
            <span>Average Cost</span>
            <span>{overview.routing.average_cost}</span>
          </div>
          <div className="tier-distribution">
            <h4>Tier Distribution</h4>
            {Object.entries(overview.routing.tier_distribution).map(([tier, count]) => (
              <div key={tier} className="tier-bar">
                <span className="tier-label">{tier}</span>
                <div className="tier-track">
                  <div
                    className="tier-fill"
                    style={{
                      width: `${overview.routing.total_requests > 0 ? (Number(count) / overview.routing.total_requests * 100) : 0}%`,
                    }}
                  />
                </div>
                <span className="tier-count">{String(count)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="detail-section">
          <h3>Orchestrator</h3>
          <div className="detail-row">
            <span>Active Agents</span>
            <span>{overview.orchestrator.active_agents}</span>
          </div>
          <div className="detail-row">
            <span>Trust Relationships</span>
            <span>{overview.orchestrator.trust_relationships}</span>
          </div>
          <div className="detail-row">
            <span>Collaboration Threads</span>
            <span>{overview.orchestrator.collaboration_threads}</span>
          </div>
        </div>
      </div>

      <style>{`
        .overview-panel { padding: 24px; max-width: 1200px; margin: 0 auto; }
        .overview-panel h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .subtitle { color: #6b7280; margin-bottom: 24px; }
        .card-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
        @media (max-width: 900px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }
        .stat-card { background: #fff; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb; display: flex; align-items: center; gap: 16px; }
        .card-icon { font-size: 2rem; }
        .card-content { display: flex; flex-direction: column; }
        .card-value { font-size: 1.8rem; font-weight: 800; color: #1f2937; }
        .card-label { font-size: 0.8rem; color: #6b7280; font-weight: 600; }
        .card-sub { font-size: 0.75rem; color: #9ca3af; }
        .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 700px) { .detail-grid { grid-template-columns: 1fr; } }
        .detail-section { background: #fff; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb; }
        .detail-section h3 { font-size: 1rem; font-weight: 700; margin-bottom: 16px; }
        .detail-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f3f4f6; }
        .detail-row span:first-child { color: #6b7280; font-size: 0.85rem; }
        .detail-row span:last-child { font-weight: 600; font-size: 0.9rem; }
        .tier-distribution { margin-top: 16px; }
        .tier-distribution h4 { font-size: 0.85rem; color: #6b7280; margin-bottom: 12px; }
        .tier-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .tier-label { font-size: 0.8rem; font-weight: 600; min-width: 60px; color: #374151; }
        .tier-track { flex: 1; height: 6px; background: #e5e7eb; border-radius: 3px; overflow: hidden; }
        .tier-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 3px; transition: width 0.5s; }
        .tier-count { font-size: 0.8rem; color: #9ca3af; min-width: 30px; text-align: right; }
        .loading { text-align: center; padding: 60px; color: #9ca3af; }
        .error-banner { background: #fef2f2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; }
      `}</style>
    </div>
  );
};