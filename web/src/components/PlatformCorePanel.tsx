import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface PlatformStats {
  platform_id: string;
  is_running: boolean;
  uptime_seconds: number;
  instances: {
    total: number;
    running: number;
    stopped: number;
    error: number;
  };
  sandboxes: {
    total: number;
    active: number;
  };
  alerts: {
    total: number;
    active: number;
    acknowledged: number;
  };
  resources: {
    max_agents: number;
    max_concurrent_sessions: number;
  };
  total_requests_served: number;
  total_errors: number;
  sync_events_total: number;
}

interface PlatformHealth {
  report_id: string;
  overall_status: string;
  component_statuses: Record<string, string>;
  active_alerts: any[];
  resource_utilization: Record<string, number>;
  agent_count: number;
  healthy_agents: number;
  degraded_agents: number;
  unhealthy_agents: number;
  timestamp: string;
}

interface RuntimeInstance {
  instance_id: string;
  agent_id: string;
  agent_name: string;
  state: string;
  started_at: string;
  last_heartbeat: string;
  uptime_seconds: number;
  memory_usage_mb: number;
  cpu_usage_percent: number;
  active_sessions: number;
  total_requests: number;
  error_count: number;
}

interface PlatformAlert {
  alert_id: string;
  severity: string;
  component: string;
  message: string;
  details: string;
  created_at: string;
  acknowledged: boolean;
  resolved_at: string | null;
}

export function PlatformCorePanel() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [instances, setInstances] = useState<RuntimeInstance[]>([]);
  const [alerts, setAlerts] = useState<PlatformAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedInstance, setSelectedInstance] = useState<RuntimeInstance | null>(null);
  const [instanceDetails, setInstanceDetails] = useState<any>(null);
  const [alertFilter, setAlertFilter] = useState<string>('all');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, healthRes, instancesRes, alertsRes] = await Promise.all([
        api.platform.stats(),
        api.platform.health(),
        api.platform.instances(),
        api.platform.alerts(),
      ]);
      setStats(statsRes);
      setHealth(healthRes);
      setInstances(instancesRes.instances || []);
      setAlerts(alertsRes.alerts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load platform data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleInstanceClick = async (instance: RuntimeInstance) => {
    setSelectedInstance(instance);
    try {
      const details = await api.platform.instanceDetails(instance.agent_id);
      setInstanceDetails(details);
    } catch {
      setInstanceDetails(null);
    }
  };

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await api.platform.acknowledgeAlert(alertId);
      loadData();
    } catch {}
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      await api.platform.resolveAlert(alertId);
      loadData();
    } catch {}
  };

  const filteredAlerts = alertFilter === 'all'
    ? alerts
    : alerts.filter(a => a.severity === alertFilter);

  const getStateColor = (state: string) => {
    switch (state) {
      case 'running': return '#22c55e';
      case 'initializing': return '#f59e0b';
      case 'stopped': case 'error': return '#ef4444';
      case 'paused': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'emergency': return '#dc2626';
      case 'warning': return '#f59e0b';
      case 'info': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#22c55e';
      case 'degraded': return '#f59e0b';
      case 'unhealthy': return '#ef4444';
      default: return '#6b7280';
    }
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header"><h2>Platform Core</h2></div>
        <div className="panel-body"><div className="loading-spinner">Loading...</div></div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Platform Core</h2>
        <span className="panel-badge">Runtime Ecosystem</span>
      </div>
      <div className="panel-body">
        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {/* System Health */}
        {health && (
          <div className="health-banner" style={{ borderColor: getStatusColor(health.overall_status) }}>
            <div className="health-status-dot" style={{ background: getStatusColor(health.overall_status) }} />
            <span className="health-status-text" style={{ color: getStatusColor(health.overall_status) }}>
              System: {health.overall_status.toUpperCase()}
            </span>
            <span className="health-meta">
              {health.healthy_agents} healthy / {health.agent_count} total agents
            </span>
          </div>
        )}

        {/* Stats Overview */}
        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.instances.total}</div>
              <div className="stat-label">Total Instances</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#22c55e' }}>{stats.instances.running}</div>
              <div className="stat-label">Running</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.sandboxes.total}</div>
              <div className="stat-label">Sandboxes</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: stats.alerts.active > 0 ? '#ef4444' : '#22c55e' }}>
                {stats.alerts.active}
              </div>
              <div className="stat-label">Active Alerts</div>
            </div>
          </div>
        )}

        {/* Resource Utilization */}
        {health && health.resource_utilization && (
          <div className="section">
            <h3>Resource Utilization</h3>
            <div className="resource-bars">
              {Object.entries(health.resource_utilization).map(([key, value]) => (
                <div key={key} className="resource-bar-item">
                  <div className="resource-bar-label">{key.replace(/_/g, ' ')}</div>
                  <div className="resource-bar-track">
                    <div
                      className="resource-bar-fill"
                      style={{
                        width: `${Math.min(value * 100, 100)}%`,
                        background: value > 0.8 ? '#ef4444' : value > 0.5 ? '#f59e0b' : '#22c55e',
                      }}
                    />
                  </div>
                  <div className="resource-bar-value">{Math.round(value * 100)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Component Statuses */}
        {health && health.component_statuses && (
          <div className="section">
            <h3>Component Status</h3>
            <div className="component-grid">
              {Object.entries(health.component_statuses).map(([component, status]) => (
                <div key={component} className="component-item">
                  <div className="component-dot" style={{ background: getStatusColor(status) }} />
                  <span className="component-name">{component.replace(/_/g, ' ')}</span>
                  <span className="component-status" style={{ color: getStatusColor(status) }}>
                    {status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Instances */}
        {instances.length > 0 && (
          <div className="section">
            <h3>Runtime Instances ({instances.length})</h3>
            <div className="instance-list">
              {instances.map((inst) => (
                <div
                  key={inst.instance_id}
                  className={`instance-item ${selectedInstance?.instance_id === inst.instance_id ? 'selected' : ''}`}
                  onClick={() => handleInstanceClick(inst)}
                >
                  <div className="instance-state-dot" style={{ background: getStateColor(inst.state) }} />
                  <div className="instance-info">
                    <div className="instance-name">{inst.agent_name}</div>
                    <div className="instance-meta">
                      {inst.state} | {inst.active_sessions} sessions | {inst.total_requests} requests
                    </div>
                  </div>
                  <div className="instance-stats">
                    <span>{inst.uptime_seconds.toFixed(0)}s uptime</span>
                    <span>{inst.error_count > 0 ? `${inst.error_count} errors` : 'No errors'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Instance Details */}
        {selectedInstance && instanceDetails && (
          <div className="section">
            <h3>Instance Details: {selectedInstance.agent_name}</h3>
            <div className="details-card">
              <div className="detail-row">
                <span className="detail-label">Agent ID</span>
                <span className="detail-value">{selectedInstance.agent_id}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">State</span>
                <span className="detail-value" style={{ color: getStateColor(selectedInstance.state) }}>
                  {selectedInstance.state}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Uptime</span>
                <span className="detail-value">{selectedInstance.uptime_seconds.toFixed(0)}s</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Active Sessions</span>
                <span className="detail-value">{selectedInstance.active_sessions}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Total Requests</span>
                <span className="detail-value">{selectedInstance.total_requests}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Errors</span>
                <span className="detail-value">{selectedInstance.error_count}</span>
              </div>
              {instanceDetails.sandboxes && (
                <div className="detail-row">
                  <span className="detail-label">Sandboxes</span>
                  <span className="detail-value">{instanceDetails.sandboxes.length}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Alerts */}
        <div className="section">
          <div className="section-header">
            <h3>Alerts ({filteredAlerts.length})</h3>
            <select
              value={alertFilter}
              onChange={(e) => setAlertFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">All</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>
          {filteredAlerts.length > 0 ? (
            <div className="alert-list">
              {filteredAlerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  className={`alert-item ${alert.acknowledged ? 'acknowledged' : ''}`}
                  style={{ borderLeftColor: getSeverityColor(alert.severity) }}
                >
                  <div className="alert-header">
                    <span className="alert-severity" style={{ background: getSeverityColor(alert.severity) }}>
                      {alert.severity}
                    </span>
                    <span className="alert-component">{alert.component}</span>
                    <span className="alert-time">{new Date(alert.created_at).toLocaleTimeString()}</span>
                  </div>
                  <div className="alert-message">{alert.message}</div>
                  {alert.details && <div className="alert-details">{alert.details}</div>}
                  <div className="alert-actions">
                    {!alert.acknowledged && (
                      <button
                        className="btn-sm"
                        onClick={() => handleAcknowledgeAlert(alert.alert_id)}
                      >
                        Acknowledge
                      </button>
                    )}
                    {!alert.resolved_at && (
                      <button
                        className="btn-sm btn-success"
                        onClick={() => handleResolveAlert(alert.alert_id)}
                      >
                        Resolve
                      </button>
                    )}
                    {alert.resolved_at && (
                      <span className="resolved-badge">Resolved</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">No active alerts</div>
          )}
        </div>

        {/* Stats footer */}
        {stats && (
          <div className="stats-footer">
            <span>Total Requests: {stats.total_requests_served.toLocaleString()}</span>
            <span>Total Errors: {stats.total_errors.toLocaleString()}</span>
            <span>Sync Events: {stats.sync_events_total}</span>
            <span>Uptime: {Math.floor(stats.uptime_seconds / 3600)}h {Math.floor((stats.uptime_seconds % 3600) / 60)}m</span>
          </div>
        )}
      </div>

      <style>{`
        .panel { height: 100%; display: flex; flex-direction: column; overflow: hidden; }
        .panel-header { display: flex; align-items: center; gap: 12px; padding: 16px 20px; border-bottom: 1px solid var(--border); }
        .panel-header h2 { margin: 0; font-size: 18px; }
        .panel-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--accent); color: #fff; }
        .panel-body { flex: 1; overflow-y: auto; padding: 20px; }
        .error-banner { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; margin-bottom: 16px; color: #b91c1c; }
        .error-banner button { background: none; border: none; color: #b91c1c; cursor: pointer; font-weight: 600; }
        .health-banner { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border: 2px solid; border-radius: 8px; margin-bottom: 20px; background: var(--card-bg); }
        .health-status-dot { width: 12px; height: 12px; border-radius: 50%; }
        .health-status-text { font-weight: 700; font-size: 14px; }
        .health-meta { margin-left: auto; font-size: 12px; color: var(--text-secondary); }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .stat-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: 700; color: var(--accent); }
        .stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
        .section { margin-bottom: 24px; }
        .section h3 { font-size: 14px; margin-bottom: 12px; color: var(--text-secondary); }
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .section-header h3 { margin-bottom: 0; }
        .filter-select { padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--card-bg); color: var(--text); font-size: 12px; }
        .resource-bars { display: flex; flex-direction: column; gap: 8px; }
        .resource-bar-item { display: flex; align-items: center; gap: 10px; }
        .resource-bar-label { width: 140px; font-size: 12px; text-transform: capitalize; }
        .resource-bar-track { flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
        .resource-bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
        .resource-bar-value { width: 40px; text-align: right; font-size: 12px; color: var(--text-secondary); }
        .component-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        .component-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; }
        .component-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .component-name { font-size: 13px; text-transform: capitalize; flex: 1; }
        .component-status { font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .instance-list { display: flex; flex-direction: column; gap: 6px; }
        .instance-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; cursor: pointer; transition: border-color 0.2s; }
        .instance-item:hover { border-color: var(--accent); }
        .instance-item.selected { border-color: var(--accent); background: rgba(99, 102, 241, 0.05); }
        .instance-state-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
        .instance-info { flex: 1; min-width: 0; }
        .instance-name { font-size: 13px; font-weight: 600; }
        .instance-meta { font-size: 11px; color: var(--text-secondary); }
        .instance-stats { display: flex; gap: 12px; font-size: 11px; color: var(--text-secondary); }
        .details-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
        .detail-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); }
        .detail-row:last-child { border-bottom: none; }
        .detail-label { font-size: 12px; color: var(--text-secondary); }
        .detail-value { font-size: 13px; font-weight: 600; }
        .alert-list { display: flex; flex-direction: column; gap: 8px; }
        .alert-item { padding: 10px 14px; background: var(--card-bg); border: 1px solid var(--border); border-left: 3px solid; border-radius: 6px; }
        .alert-item.acknowledged { opacity: 0.7; }
        .alert-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
        .alert-severity { font-size: 10px; padding: 1px 6px; border-radius: 4px; color: #fff; text-transform: uppercase; font-weight: 700; }
        .alert-component { font-size: 12px; font-weight: 600; }
        .alert-time { margin-left: auto; font-size: 11px; color: var(--text-secondary); }
        .alert-message { font-size: 13px; margin-bottom: 4px; }
        .alert-details { font-size: 11px; color: var(--text-secondary); margin-bottom: 8px; }
        .alert-actions { display: flex; gap: 6px; }
        .btn-sm { padding: 3px 10px; font-size: 11px; border: 1px solid var(--border); border-radius: 4px; background: var(--card-bg); color: var(--text); cursor: pointer; }
        .btn-sm:hover { background: var(--border); }
        .btn-success { border-color: #22c55e; color: #22c55e; }
        .btn-success:hover { background: #dcfce7; }
        .resolved-badge { font-size: 11px; color: #22c55e; font-weight: 600; }
        .empty-state { text-align: center; padding: 20px; color: var(--text-secondary); font-size: 13px; }
        .stats-footer { display: flex; gap: 16px; padding: 12px 0; border-top: 1px solid var(--border); font-size: 11px; color: var(--text-secondary); }
        .loading-spinner { text-align: center; padding: 40px; color: var(--text-secondary); }
      `}</style>
    </div>
  );
}