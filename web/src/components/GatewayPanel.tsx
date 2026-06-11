import React, { useState, useEffect } from 'react';
import type { GatewayStats, GatewaySession } from '../types';
import { api } from '../api/client';

export const GatewayPanel: React.FC = () => {
  const [stats, setStats] = useState<GatewayStats | null>(null);
  const [sessions, setSessions] = useState<GatewaySession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectPlatform, setConnectPlatform] = useState('telegram');
  const [connectConfig, setConnectConfig] = useState('');
  const [connecting, setConnecting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, sess] = await Promise.all([
        api.gateway.stats(),
        api.gateway.sessions(),
      ]);
      setStats(s);
      setSessions(sess);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load gateway data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      await api.gateway.connectPlatform(connectPlatform, connectConfig);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
    } finally {
      setConnecting(false);
    }
  };

  if (loading) {
    return <div className="panel-container"><div className="panel-loading">Loading gateway data...</div></div>;
  }

  const platformList = stats ? Object.keys(stats.platforms) : [];
  const platformIcons: Record<string, string> = {
    web: '\u{1F310}',
    cli: '\u{2328}\u{FE0F}',
    telegram: '\u{1F4E8}',
    discord: '\u{1F4AC}',
    slack: '\u{1F4BC}',
  };

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Message Gateway</h2>
          <div className="panel-subtitle">Multi-platform messaging integration hub</div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Stats */}
      {stats && (
        <div className="memory-stats-grid">
          <div className="memory-stat-card">
            <div className="memory-stat-value">{platformList.length}</div>
            <div className="memory-stat-label">Platforms</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{stats.active_sessions}</div>
            <div className="memory-stat-label">Active Sessions</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{stats.total_messages}</div>
            <div className="memory-stat-label">Total Messages</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">
              <span style={{ color: stats.running ? '#10b981' : '#ef4444' }}>{'\u25CF'}</span>
            </div>
            <div className="memory-stat-label">{stats.running ? 'Running' : 'Stopped'}</div>
          </div>
        </div>
      )}

      {/* Platform Connection */}
      <div className="dashboard-section">
        <h3>Connect Platform</h3>
        <div className="form-row">
          <div className="form-group">
            <label>Platform</label>
            <select value={connectPlatform} onChange={e => setConnectPlatform(e.target.value)}>
              <option value="telegram">Telegram</option>
              <option value="discord">Discord</option>
              <option value="slack">Slack</option>
            </select>
          </div>
          <div className="form-group">
            <label>Config (JSON)</label>
            <input
              type="text"
              value={connectConfig}
              onChange={e => setConnectConfig(e.target.value)}
              placeholder='{"bot_token": "..."}'
            />
          </div>
        </div>
        <button className="btn-primary" onClick={handleConnect} disabled={connecting}>
          {connecting ? 'Connecting...' : 'Connect'}
        </button>
      </div>

      {/* Connected Platforms */}
      <div className="dashboard-section">
        <h3>Connected Platforms</h3>
        {platformList.length === 0 ? (
          <div className="panel-empty">No external platforms connected. Web adapter is always active.</div>
        ) : (
          <div className="dashboard-agent-grid">
            {platformList.map(platform => (
              <div key={platform} className="dashboard-agent-card">
                <div className="dashboard-agent-avatar" style={{
                  background: platform === 'web' ? '#3b82f6' : platform === 'telegram' ? '#0088cc' : '#6366f1',
                }}>
                  {platformIcons[platform] || '\u{1F4E1}'}
                </div>
                <div className="dashboard-agent-info">
                  <div className="dashboard-agent-name" style={{ textTransform: 'capitalize' }}>{platform}</div>
                  <div className="dashboard-agent-role">{stats?.platforms[platform]}</div>
                </div>
                <span className={`dashboard-badge ${stats?.platforms[platform] === 'connected' ? 'active' : 'inactive'}`}>
                  {stats?.platforms[platform]}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Active Sessions */}
      <div className="dashboard-section">
        <h3>Active Sessions ({sessions.length})</h3>
        {sessions.length === 0 ? (
          <div className="panel-empty">No active gateway sessions.</div>
        ) : (
          <div className="subagent-tasks">
            {sessions.map(session => (
              <div key={session.id} className="skill-card" style={{ cursor: 'default' }}>
                <div className="skill-card-icon">{platformIcons[session.platform] || '\u{1F4E1}'}</div>
                <div className="skill-card-info">
                  <div className="skill-card-name">{session.platform_user_id}</div>
                  <div className="skill-card-desc">
                    Agent: {session.agent_id} · Messages: {session.message_count}
                  </div>
                  <div className="skill-card-cat">
                    {session.platform} · Last active: {new Date(session.last_active).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};