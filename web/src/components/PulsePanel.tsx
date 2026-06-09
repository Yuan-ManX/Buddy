import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

export const PulsePanel: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'components' | 'anomalies'>('overview');
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const toast = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      const [h, a] = await Promise.all([
        api.pulse.health(),
        api.pulse.anomalies(),
      ]);
      setHealth(h);
      setAnomalies(Array.isArray(a?.alerts) ? a.alerts : []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load pulse data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // auto-refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#10b981';
      case 'degraded': return '#f59e0b';
      case 'unhealthy': return '#f97316';
      case 'critical': return '#ef4444';
      default: return '#94a3b8';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'healthy': return 'rgba(16,185,129,0.1)';
      case 'degraded': return 'rgba(245,158,11,0.1)';
      case 'unhealthy': return 'rgba(249,115,22,0.1)';
      case 'critical': return 'rgba(239,68,68,0.1)';
      default: return 'rgba(148,163,184,0.1)';
    }
  };

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  if (loading) return (
    <div className="panel-container">
      <div className="panel-loading">
        <div className="dashboard-spinner"></div>
        <div>Loading health data...</div>
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
          <h2>BuddyPulse</h2>
          <div className="panel-subtitle">Health Monitoring & Metrics</div>
        </div>
        <button className="btn-sm" onClick={loadData}>Refresh</button>
      </div>

      {/* Overall Status */}
      {health && (
        <div className="nexus-summary-bar">
          <div className="nexus-stat-item">
            <div className="dashboard-stat-value" style={{ color: getStatusColor(health.overall_status) }}>
              {health.overall_status?.toUpperCase()}
            </div>
            <div className="dashboard-stat-label">System Status</div>
          </div>
          <div className="nexus-stat-item">
            <div className="dashboard-stat-value">{health.active_components}</div>
            <div className="dashboard-stat-label">Active Components</div>
          </div>
          <div className="nexus-stat-item">
            <div className="dashboard-stat-value">{formatUptime(health.total_uptime_seconds)}</div>
            <div className="dashboard-stat-label">Uptime</div>
          </div>
          <div className="nexus-stat-item">
            <div className="dashboard-stat-value" style={{ color: health.degraded_components > 0 ? '#f59e0b' : '#10b981' }}>
              {health.degraded_components}
            </div>
            <div className="dashboard-stat-label">Degraded</div>
          </div>
          <div className="nexus-stat-item">
            <div className="dashboard-stat-value" style={{ color: health.unhealthy_components > 0 ? '#ef4444' : '#10b981' }}>
              {health.unhealthy_components}
            </div>
            <div className="dashboard-stat-label">Unhealthy</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        <button className={`forge-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={`forge-tab ${activeTab === 'components' ? 'active' : ''}`} onClick={() => setActiveTab('components')}>
          Components ({health?.components?.length || 0})
        </button>
        <button className={`forge-tab ${activeTab === 'anomalies' ? 'active' : ''}`} onClick={() => setActiveTab('anomalies')}>
          Anomalies ({anomalies.length})
        </button>
      </div>

      {/* Components Tab */}
      {activeTab === 'components' && (
        <div>
          {!health?.components || health.components.length === 0 ? (
            <div className="panel-empty">No components registered</div>
          ) : (
            <div className="forge-skill-list">
              {health.components.map((comp: any) => (
                <div key={comp.component_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{comp.name || comp.component_id}</div>
                    <div className="dashboard-badge" style={{ background: getStatusBg(comp.status), color: getStatusColor(comp.status) }}>
                      {comp.status}
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      <span>P50: {comp.latency_p50_ms?.toFixed(1) || 'N/A'}ms</span> ·
                      <span> P99: {comp.latency_p99_ms?.toFixed(1) || 'N/A'}ms</span> ·
                      <span> Error Rate: {comp.error_rate ? `${(comp.error_rate * 100).toFixed(2)}%` : 'N/A'}</span>
                    </div>
                    <div className="text-xs text-muted">
                      Uptime: {formatUptime(comp.uptime_seconds || 0)} ·
                      Last heartbeat: {comp.last_heartbeat ? new Date(comp.last_heartbeat * 1000).toLocaleString() : 'N/A'}
                    </div>
                    <div style={{ marginTop: '8px' }}>
                      <div className="text-xs text-muted mb-1">Health</div>
                      <div className="dashboard-progress-bar">
                        <div
                          className="dashboard-progress-fill"
                          style={{
                            width: comp.status === 'healthy' ? '100%' : comp.status === 'degraded' ? '65%' : comp.status === 'unhealthy' ? '30%' : '10%',
                            background: getStatusColor(comp.status),
                          }}
                        />
                      </div>
                    </div>
                    {comp.metadata && Object.keys(comp.metadata).length > 0 && (
                      <div style={{ marginTop: '8px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {Object.entries(comp.metadata).map(([k, v]) => (
                          <span key={k} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Anomalies Tab */}
      {activeTab === 'anomalies' && (
        <div>
          {anomalies.length === 0 ? (
            <div className="panel-empty">No anomalies detected</div>
          ) : (
            <div className="forge-skill-list">
              {anomalies.map((anomaly: any, idx: number) => (
                <div key={idx} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{anomaly.message || 'Anomaly detected'}</div>
                    <div className="dashboard-badge" style={{ background: getStatusBg(anomaly.severity || 'degraded'), color: getStatusColor(anomaly.severity || 'degraded') }}>
                      {anomaly.severity || 'unknown'}
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    {anomaly.component_id && <div>Component: {anomaly.component_id}</div>}
                    {anomaly.details && (
                      <pre style={{ fontSize: '0.75rem', marginTop: '4px', color: 'var(--text-muted)', background: 'var(--bg-elevated)', padding: '8px', borderRadius: '4px' }}>
                        {JSON.stringify(anomaly.details, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recent Alerts in Overview */}
      {activeTab === 'overview' && health?.recent_alerts && (
        <div className="dashboard-section">
          <h3>Recent Alerts</h3>
          {health.recent_alerts.length === 0 ? (
            <div className="text-sm text-muted">No recent alerts</div>
          ) : (
            health.recent_alerts.map((alert: any, idx: number) => (
              <div key={idx} className="dashboard-stat-row" style={{ padding: '8px 0', borderBottom: '1px solid var(--border-light)' }}>
                <span style={{ color: getStatusColor(alert.severity || 'low'), fontWeight: '600' }}>
                  {alert.component_id || 'System'}
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {alert.message || 'Alert'}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};