import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { Agent, CompressedTrajectory } from '../types';

interface Props {
  agent: Agent;
}

export const TrajectoryPanel: React.FC<Props> = ({ agent }) => {
  const [trajectories, setTrajectories] = useState<CompressedTrajectory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'successful' | 'failed'>('all');
  const [selectedTrajectory, setSelectedTrajectory] = useState<CompressedTrajectory | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [traceName, setTraceName] = useState('');
  const [traceTaskId, setTraceTaskId] = useState('');
  const toast = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      const [s, t] = await Promise.all([
        api.trajectory.stats(),
        filter === 'all'
          ? api.trajectory.byAgent(agent.id, 50)
          : filter === 'successful'
          ? api.trajectory.successful(50)
          : api.trajectory.failed(50),
      ]);
      setStats(s);
      setTrajectories(Array.isArray(t) ? t : []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load trajectory data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [agent.id, filter]);

  const handleStartTrace = async () => {
    try {
      await api.trajectory.start(agent.id, traceTaskId || undefined);
      toast.success('Trace started');
      setTraceName('');
      setTraceTaskId('');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const getStatusColor = (success: boolean) => success ? '#10b981' : '#ef4444';

  if (loading) return (
    <div className="panel-container">
      <div className="panel-loading">
        <div className="dashboard-spinner"></div>
        <div>Loading trajectory data...</div>
      </div>
    </div>
  );

  if (error) return (
    <div className="panel-container">
      <div className="error-banner">
        {error}
        <button onClick={loadData} className="btn-sm" style={{ marginLeft: '8px' }}>Retry</button>
      </div>
    </div>
  );

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Buddy Trajectory</h2>
          <div className="panel-subtitle">Execution History & Learning</div>
        </div>
        <div className="panel-header-actions">
          <button className="btn-sm" onClick={handleStartTrace}>Start New Trace</button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="nexus-summary-bar">
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{stats?.total_compressed || 0}</div>
          <div className="dashboard-stat-label">Total Compressed</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{stats?.active_traces || 0}</div>
          <div className="dashboard-stat-label">Active Traces</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value" style={{ color: '#10b981' }}>{stats?.successful || 0}</div>
          <div className="dashboard-stat-label">Successful</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value" style={{ color: '#ef4444' }}>{stats?.failed || 0}</div>
          <div className="dashboard-stat-label">Failed</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">
            {stats?.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : 'N/A'}
          </div>
          <div className="dashboard-stat-label">Success Rate</div>
        </div>
      </div>

      {/* Filter */}
      <div className="skill-categories" style={{ margin: '16px 0' }}>
        <button
          className={`skill-cat-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All
        </button>
        <button
          className={`skill-cat-btn ${filter === 'successful' ? 'active' : ''}`}
          onClick={() => setFilter('successful')}
        >
          Successful
        </button>
        <button
          className={`skill-cat-btn ${filter === 'failed' ? 'active' : ''}`}
          onClick={() => setFilter('failed')}
        >
          Failed
        </button>
      </div>

      {/* Trajectory List */}
      {trajectories.length === 0 ? (
        <div className="panel-empty">No trajectory records yet</div>
      ) : (
        <div className="forge-skill-list">
          {trajectories.map((t, idx) => (
            <div
              key={t.original_trace_id || idx}
              className="forge-skill-card"
              onClick={() => setSelectedTrajectory(t)}
              style={{ cursor: 'pointer' }}
            >
              <div className="forge-skill-header">
                <div className="forge-skill-name">
                  {t.summary?.substring(0, 80) || 'Trace'}
                  {t.summary && t.summary.length > 80 ? '...' : ''}
                </div>
                <div
                  className={`dashboard-badge ${t.success ? 'active' : 'inactive'}`}
                  style={{ background: t.success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', color: getStatusColor(t.success) }}
                >
                  {t.success ? 'Success' : 'Failed'}
                </div>
              </div>
              <div className="forge-skill-meta">
                <div>Agent: {t.agent_id}</div>
                <div>
                  <span>Quality: {(t.quality_score * 100).toFixed(0)}%</span> ·
                  <span> Steps: {t.num_steps_original} → {t.num_steps_compressed}</span> ·
                  <span> Tokens saved: {t.tokens_saved}</span>
                </div>
                <div className="text-xs text-muted">
                  Compressed: {new Date(t.compressed_at).toLocaleString()}
                </div>
                {t.key_decisions && t.key_decisions.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <div className="text-xs text-muted mb-1">Key Decisions:</div>
                    {t.key_decisions.slice(0, 3).map((d, i) => (
                      <div key={i} className="text-xs" style={{ color: 'var(--text-secondary)', paddingLeft: '8px' }}>
                        • {d}
                      </div>
                    ))}
                  </div>
                )}
                {t.tools_used && t.tools_used.length > 0 && (
                  <div style={{ marginTop: '4px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {t.tools_used.map(tool => (
                      <span key={tool} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                        {tool}
                      </span>
                    ))}
                  </div>
                )}
                {t.patterns_extracted && t.patterns_extracted.length > 0 && (
                  <div style={{ marginTop: '4px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {t.patterns_extracted.map((p, i) => (
                      <span key={i} className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded">
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Trajectory Detail Modal */}
      {selectedTrajectory && (
        <div className="modal-overlay" onClick={() => setSelectedTrajectory(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <h2>Trajectory Detail</h2>
            <div style={{ marginBottom: '16px' }}>
              <div className="dashboard-stat-row">
                <span>Status</span>
                <strong style={{ color: getStatusColor(selectedTrajectory.success) }}>
                  {selectedTrajectory.success ? 'Successful' : 'Failed'}
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Quality Score</span>
                <strong>{(selectedTrajectory.quality_score * 100).toFixed(0)}%</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Steps (Original → Compressed)</span>
                <strong>{selectedTrajectory.num_steps_original} → {selectedTrajectory.num_steps_compressed}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Tokens Saved</span>
                <strong>{selectedTrajectory.tokens_saved}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Compressed At</span>
                <strong>{new Date(selectedTrajectory.compressed_at).toLocaleString()}</strong>
              </div>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <div className="text-xs text-muted mb-1">Summary:</div>
              <p style={{ fontSize: '0.9rem', color: 'var(--text)', lineHeight: '1.6' }}>
                {selectedTrajectory.summary}
              </p>
            </div>
            {selectedTrajectory.key_decisions?.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div className="text-xs text-muted mb-1">Key Decisions:</div>
                {selectedTrajectory.key_decisions.map((d, i) => (
                  <div key={i} style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', padding: '4px 8px' }}>
                    {i + 1}. {d}
                  </div>
                ))}
              </div>
            )}
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setSelectedTrajectory(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};