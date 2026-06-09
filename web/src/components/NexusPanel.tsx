import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { RuntimeInfo, NexusSummary } from '../types';

const PLATFORM_EMOJIS: Record<string, string> = {
  web: '🌐',
  cli: '💻',
  api: '🔌',
  mobile: '📱',
  desktop: '🖥️',
  embedded: '⚙️',
};

const STATUS_COLORS: Record<string, string> = {
  connected: '#10b981',
  disconnected: '#9ca3af',
  error: '#ef4444',
};

export const NexusPanel: React.FC = () => {
  const [summary, setSummary] = useState<NexusSummary | null>(null);
  const [runtimes, setRuntimes] = useState<RuntimeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [platformFilter, setPlatformFilter] = useState<string>('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [s, r] = await Promise.all([
        api.nexus.summary(),
        api.nexus.runtimes(platformFilter || undefined),
      ]);
      setSummary(s);
      setRuntimes(r);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load nexus data');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (platform: string) => {
    setPlatformFilter(prev => (prev === platform ? '' : platform));
  };

  useEffect(() => {
    if (!loading) {
      loadData();
    }
  }, [platformFilter]);

  const getPlatformEmoji = (platform: string) => PLATFORM_EMOJIS[platform.toLowerCase()] || '🔗';

  const getStatusColor = (status: string) => STATUS_COLORS[status.toLowerCase()] || '#6b7280';

  const formatTime = (iso: string) => {
    if (!iso) return 'N/A';
    const d = new Date(iso);
    return d.toLocaleString();
  };

  // ── Loading State ──
  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Buddy Nexus</h2>
          <p className="panel-subtitle">Runtime & Platform Management Hub</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading nexus data...</span>
        </div>
        <style>{nexusStyles}</style>
      </div>
    );
  }

  // ── Error State ──
  if (error && !summary) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Buddy Nexus</h2>
          <p className="panel-subtitle">Runtime & Platform Management Hub</p>
        </div>
        <div className="panel-error">
          <p>{error}</p>
          <button className="retry-btn" onClick={() => { setLoading(true); setError(null); loadData(); }}>
            Retry
          </button>
        </div>
        <style>{nexusStyles}</style>
      </div>
    );
  }

  const platforms = summary
    ? Object.keys(summary.platform_distribution || {})
    : [];

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Buddy Nexus</h2>
        <p className="panel-subtitle">Runtime & Platform Management Hub</p>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* ── Summary Bar ── */}
      {summary && (
        <div className="nexus-summary-bar">
          <div className="nexus-stat-item">
            <span className="stat-icon">🖧</span>
            <div className="stat-content">
              <span className="stat-value">{summary.total_runtimes}</span>
              <span className="stat-label">Total Runtimes</span>
            </div>
          </div>
          <div className="nexus-stat-item">
            <span className="stat-icon">🌐</span>
            <div className="stat-content">
              <span className="stat-value">{summary.connected_platforms}</span>
              <span className="stat-label">Connected Platforms</span>
            </div>
          </div>
          <div className="nexus-stat-item">
            <span className="stat-icon">📊</span>
            <div className="stat-content">
              <span className="stat-value">{summary.total_requests.toLocaleString()}</span>
              <span className="stat-label">Total Requests</span>
            </div>
          </div>
          <div className="nexus-stat-item">
            <span className="stat-icon">⚠️</span>
            <div className="stat-content">
              <span className="stat-value" style={{ color: summary.total_errors > 0 ? '#ef4444' : undefined }}>
                {summary.total_errors.toLocaleString()}
              </span>
              <span className="stat-label">Total Errors</span>
            </div>
          </div>
          <div className="nexus-stat-item">
            <span className="stat-icon">{summary.monitor_running ? '🟢' : '🔴'}</span>
            <div className="stat-content">
              <span className="stat-value" style={{ color: summary.monitor_running ? '#10b981' : '#ef4444' }}>
                {summary.monitor_running ? 'Running' : 'Stopped'}
              </span>
              <span className="stat-label">Monitor</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Platform Distribution (status breakdown) ── */}
      {summary && Object.keys(summary.status_distribution || {}).length > 0 && (
        <div className="status-distribution">
          {Object.entries(summary.status_distribution).map(([status, count]) => (
            <span
              key={status}
              className="status-chip"
              style={{ backgroundColor: getStatusColor(status), color: '#fff' }}
            >
              {status}: {String(count)}
            </span>
          ))}
        </div>
      )}

      {/* ── Platform Filter Buttons ── */}
      <div className="platform-filters">
        <button
          className={`filter-btn ${platformFilter === '' ? 'active' : ''}`}
          onClick={() => setPlatformFilter('')}
        >
          All
        </button>
        {platforms.map(platform => (
          <button
            key={platform}
            className={`filter-btn ${platformFilter === platform ? 'active' : ''}`}
            onClick={() => handleFilterChange(platform)}
          >
            {getPlatformEmoji(platform)} {platform}
          </button>
        ))}
      </div>

      {/* ── Runtime Grid ── */}
      {runtimes.length > 0 ? (
        <div className="nexus-runtime-grid">
          {runtimes.map(rt => (
            <div key={rt.runtime_id} className="nexus-runtime-card">
              <div className="nexus-runtime-header">
                <span className="nexus-runtime-name">
                  {getPlatformEmoji(rt.platform)} {rt.runtime_id}
                </span>
                <span
                  className={`nexus-runtime-status ${rt.status.toLowerCase()}`}
                  style={{ color: getStatusColor(rt.status) }}
                >
                  ● {rt.status}
                </span>
              </div>

              <div className="nexus-runtime-detail">
                <div className="nexus-runtime-meta">
                  <span className="meta-label">Platform</span>
                  <span className="meta-value">{rt.platform}</span>
                </div>
                <div className="nexus-runtime-meta">
                  <span className="meta-label">Agent</span>
                  <span className="meta-value">{rt.agent_id}</span>
                </div>
                <div className="nexus-runtime-meta">
                  <span className="meta-label">Requests</span>
                  <span className="meta-value">{rt.request_count.toLocaleString()}</span>
                </div>
                <div className="nexus-runtime-meta">
                  <span className="meta-label">Errors</span>
                  <span className="meta-value" style={{ color: rt.error_count > 0 ? '#ef4444' : undefined }}>
                    {rt.error_count}
                  </span>
                </div>
                <div className="nexus-runtime-meta">
                  <span className="meta-label">Connected</span>
                  <span className="meta-value">{formatTime(rt.connected_at)}</span>
                </div>
                <div className="nexus-runtime-meta">
                  <span className="meta-label">Last Heartbeat</span>
                  <span className="meta-value">{formatTime(rt.last_heartbeat)}</span>
                </div>
              </div>

              {rt.capabilities && rt.capabilities.length > 0 && (
                <div className="capabilities-list">
                  <span className="capabilities-label">Capabilities</span>
                  <div className="capability-chips">
                    {rt.capabilities.map(cap => (
                      <span key={cap} className="capability-chip">{cap}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="panel-empty">
          <span className="empty-icon">📡</span>
          <p>No runtimes connected</p>
          <p className="empty-hint">
            {platformFilter
              ? `No runtimes found for platform "${platformFilter}". Try a different filter.`
              : 'Register a runtime to start receiving heartbeats and managing connections.'}
          </p>
        </div>
      )}

      <style>{nexusStyles}</style>
    </div>
  );
};

const nexusStyles = `
  .panel-container {
    padding: 24px;
    max-width: 1200px;
    margin: 0 auto;
  }
  .panel-header h2 {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 4px;
    color: var(--text, #1f2937);
  }
  .panel-subtitle {
    color: var(--text-secondary, #6b7280);
    margin-bottom: 24px;
    font-size: 0.9rem;
  }

  /* Loading */
  .panel-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 0;
    color: var(--text-secondary, #9ca3af);
    gap: 16px;
    font-size: 0.95rem;
  }
  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--border, #e5e7eb);
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Error */
  .panel-error {
    text-align: center;
    padding: 60px 0;
    color: var(--text-secondary, #6b7280);
  }
  .panel-error p {
    margin-bottom: 16px;
    color: #ef4444;
    font-size: 0.95rem;
  }
  .retry-btn {
    padding: 10px 24px;
    background: #3b82f6;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.9rem;
  }
  .retry-btn:hover {
    background: #2563eb;
  }
  .error-banner {
    background: #fef2f2;
    color: #991b1b;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 0.85rem;
  }

  /* Summary Bar */
  .nexus-summary-bar {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }
  .nexus-stat-item {
    flex: 1;
    min-width: 160px;
    background: var(--bg-card, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .stat-icon {
    font-size: 1.6rem;
  }
  .stat-content {
    display: flex;
    flex-direction: column;
  }
  .stat-value {
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--text, #1f2937);
  }
  .stat-label {
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);
    font-weight: 600;
  }

  /* Status Distribution Chips */
  .status-distribution {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .status-chip {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: capitalize;
  }

  /* Platform Filters */
  .platform-filters {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }
  .filter-btn {
    padding: 8px 16px;
    border: 1px solid var(--border, #d1d5db);
    border-radius: 8px;
    background: var(--bg-card, #fff);
    color: var(--text, #374151);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .filter-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }
  .filter-btn.active {
    background: #3b82f6;
    color: #fff;
    border-color: #3b82f6;
  }

  /* Runtime Grid */
  .nexus-runtime-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
  }
  .nexus-runtime-card {
    background: var(--bg-card, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 20px;
    transition: box-shadow 0.2s;
  }
  .nexus-runtime-card:hover {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  }

  /* Runtime Header */
  .nexus-runtime-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border, #f3f4f6);
  }
  .nexus-runtime-name {
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--text, #1f2937);
  }
  .nexus-runtime-status {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: capitalize;
  }
  .nexus-runtime-status.connected {
    color: #10b981;
  }
  .nexus-runtime-status.disconnected {
    color: #9ca3af;
  }
  .nexus-runtime-status.error {
    color: #ef4444;
  }

  /* Runtime Detail */
  .nexus-runtime-detail {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 14px;
  }
  .nexus-runtime-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .meta-label {
    font-size: 0.8rem;
    color: var(--text-secondary, #6b7280);
  }
  .meta-value {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text, #374151);
    max-width: 55%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Capabilities */
  .capabilities-list {
    margin-top: 4px;
    padding-top: 12px;
    border-top: 1px solid var(--border, #f3f4f6);
  }
  .capabilities-label {
    font-size: 0.75rem;
    color: var(--text-secondary, #6b7280);
    font-weight: 600;
    display: block;
    margin-bottom: 8px;
  }
  .capability-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .capability-chip {
    padding: 3px 10px;
    background: var(--bg-card, #f3f4f6);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-secondary, #4b5563);
  }

  /* Empty State */
  .panel-empty {
    text-align: center;
    padding: 60px 0;
    color: var(--text-secondary, #9ca3af);
  }
  .empty-icon {
    font-size: 3rem;
    display: block;
    margin-bottom: 12px;
  }
  .panel-empty p {
    font-size: 0.95rem;
    margin-bottom: 6px;
  }
  .empty-hint {
    font-size: 0.8rem;
    color: var(--text-secondary, #9ca3af);
    max-width: 400px;
    margin: 0 auto;
    line-height: 1.5;
  }
`;

export default NexusPanel;