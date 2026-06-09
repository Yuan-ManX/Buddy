import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

export const GuardPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'alerts' | 'check'>('overview');
  const [checkAgentId, setCheckAgentId] = useState('');
  const [checkContent, setCheckContent] = useState('');
  const [checkResult, setCheckResult] = useState<any>(null);
  const [rateLimitAgent, setRateLimitAgent] = useState('');
  const [rateLimitResult, setRateLimitResult] = useState<any>(null);
  const toast = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      const [s, a] = await Promise.all([
        api.guard.stats(),
        api.guard.alerts(),
      ]);
      setStats(s);
      setAlerts(Array.isArray(a) ? a : []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load guard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCheckContent = async () => {
    if (!checkAgentId.trim() || !checkContent.trim()) return;
    try {
      const result = await api.guard.checkContent(checkAgentId.trim(), checkContent);
      setCheckResult(result);
      toast.info(result.allowed ? 'Content check passed' : 'Content flagged');
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCheckRateLimit = async () => {
    if (!rateLimitAgent.trim()) return;
    try {
      const result = await api.guard.checkRateLimit(rateLimitAgent.trim());
      setRateLimitResult(result);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleClearAlerts = async () => {
    try {
      await api.guard.clearAlerts();
      toast.success('Alerts cleared');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'high': return '#f97316';
      case 'medium': return '#f59e0b';
      case 'low': return '#3b82f6';
      default: return '#94a3b8';
    }
  };

  if (loading) return (
    <div className="panel-container">
      <div className="panel-loading">
        <div className="dashboard-spinner"></div>
        <div>Loading guard data...</div>
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
          <h2>BuddyGuard</h2>
          <div className="panel-subtitle">Safety Monitoring & Security</div>
        </div>
        <button className="btn-sm btn-danger" onClick={handleClearAlerts}>Clear Alerts</button>
      </div>

      {/* Stats Bar */}
      <div className="nexus-summary-bar">
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value" style={{ color: '#10b981' }}>{stats?.total_allowed || 0}</div>
          <div className="dashboard-stat-label">Allowed</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value" style={{ color: '#ef4444' }}>{stats?.total_blocked || 0}</div>
          <div className="dashboard-stat-label">Blocked</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{stats?.total_checks || 0}</div>
          <div className="dashboard-stat-label">Total Checks</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{stats?.total_alerts || 0}</div>
          <div className="dashboard-stat-label">Alerts</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{stats?.total_audits || 0}</div>
          <div className="dashboard-stat-label">Audits</div>
        </div>
      </div>

      {/* Action Breakdown */}
      {stats?.by_action && (
        <div className="dashboard-section" style={{ marginTop: '16px' }}>
          <h3>Actions Breakdown</h3>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {Object.entries(stats.by_action).map(([action, count]: [string, any]) => (
              <div key={action} style={{ background: 'var(--bg-elevated)', padding: '12px 16px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: '700', color: 'var(--text)' }}>{count}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{action}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        <button className={`forge-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={`forge-tab ${activeTab === 'alerts' ? 'active' : ''}`} onClick={() => setActiveTab('alerts')}>Alerts ({alerts.length})</button>
        <button className={`forge-tab ${activeTab === 'check' ? 'active' : ''}`} onClick={() => setActiveTab('check')}>Check</button>
      </div>

      {/* Alerts Tab */}
      {activeTab === 'alerts' && (
        <div>
          {alerts.length === 0 ? (
            <div className="panel-empty">No alerts</div>
          ) : (
            <div className="forge-skill-list">
              {alerts.map((alert, idx) => (
                <div key={alert.alert_id || idx} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.85rem' }}>
                      {alert.action}
                    </div>
                    <div className="dashboard-badge" style={{ background: `${getSeverityColor(alert.severity)}15`, color: getSeverityColor(alert.severity) }}>
                      {alert.severity}
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{alert.message}</div>
                    <div className="text-xs text-muted">
                      Agent: {alert.agent_id} · {new Date(alert.timestamp).toLocaleString()}
                    </div>
                    {alert.details && (
                      <pre style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg-elevated)', padding: '8px', borderRadius: '4px', marginTop: '4px', overflowX: 'auto' }}>
                        {JSON.stringify(alert.details, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Check Tab */}
      {activeTab === 'check' && (
        <div>
          <div className="dashboard-section">
            <h3>Content Safety Check</h3>
            <div className="form-group">
              <label>Agent ID</label>
              <input type="text" placeholder="agent-..." value={checkAgentId} onChange={e => setCheckAgentId(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea rows={3} placeholder="Enter content to check..." value={checkContent} onChange={e => setCheckContent(e.target.value)} />
            </div>
            <button className="btn-primary" onClick={handleCheckContent}>Check Content</button>
            {checkResult && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                borderRadius: '8px',
                background: checkResult.allowed ? 'rgba(16,185,129,0.05)' : 'rgba(239,68,68,0.05)',
                border: `1px solid ${checkResult.allowed ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
              }}>
                <div style={{ fontWeight: '700', color: checkResult.allowed ? '#10b981' : '#ef4444', marginBottom: '4px' }}>
                  {checkResult.allowed ? 'Content Passed' : 'Content Flagged'}
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{checkResult.reason}</div>
                {checkResult.details && (
                  <pre style={{ fontSize: '0.75rem', marginTop: '8px', color: 'var(--text-muted)' }}>
                    {JSON.stringify(checkResult.details, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>

          <div className="dashboard-section">
            <h3>Rate Limit Check</h3>
            <div className="form-group">
              <label>Agent ID</label>
              <input type="text" placeholder="agent-..." value={rateLimitAgent} onChange={e => setRateLimitAgent(e.target.value)} />
            </div>
            <button className="btn-primary" onClick={handleCheckRateLimit}>Check Rate Limit</button>
            {rateLimitResult && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                borderRadius: '8px',
                background: rateLimitResult.allowed ? 'rgba(16,185,129,0.05)' : 'rgba(239,68,68,0.05)',
                border: `1px solid ${rateLimitResult.allowed ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
              }}>
                <div style={{ fontWeight: '700', color: rateLimitResult.allowed ? '#10b981' : '#ef4444' }}>
                  {rateLimitResult.allowed ? 'Within Limits' : 'Rate Limited'}
                </div>
                <pre style={{ fontSize: '0.75rem', marginTop: '4px', color: 'var(--text-muted)' }}>
                  {JSON.stringify(rateLimitResult.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};