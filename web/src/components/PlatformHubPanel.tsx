import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface SubsystemInfo {
  name: string;
  status: string;
  started_at: string;
  error_count: number;
  last_error: string;
}

interface PlatformHealth {
  overall: string;
  is_running: boolean;
  startup_time: string;
  uptime_seconds: number;
  subsystems: Record<string, SubsystemInfo>;
  health_ratio: number;
  subsystem_count: {
    total: number;
    running: number;
    degraded: number;
    error: number;
    stopped: number;
  };
}

interface PlatformStats {
  is_running: boolean;
  startup_time: string;
  uptime_seconds: number;
  subsystem_count: number;
  events: { total: number; max: number };
  listener_count: number;
  health: PlatformHealth;
}

interface PlatformEvent {
  id: string;
  source: string;
  event_type: string;
  severity: string;
  data: Record<string, unknown>;
  timestamp: string;
}

const STATUS_COLORS: Record<string, string> = {
  running: '#10b981',
  healthy: '#10b981',
  degraded: '#f59e0b',
  unhealthy: '#ef4444',
  critical: '#dc2626',
  error: '#ef4444',
  stopped: '#9ca3af',
  starting: '#3b82f6',
  uninitialized: '#d1d5db',
};

const SEVERITY_ICONS: Record<string, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  error: '❌',
  critical: '🚨',
};

export const PlatformHubPanel: React.FC = () => {
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [events, setEvents] = useState<PlatformEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [eventFilter, setEventFilter] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [configOpen, setConfigOpen] = useState(false);
  const [configForm, setConfigForm] = useState({
    auto_restart_subsystems: true,
    health_check_interval_ms: 30000,
    max_subsystem_restarts: 3,
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [healthData, statsData, eventsData] = await Promise.all([
        api.platformHub.health().catch(() => null),
        api.platformHub.stats().catch(() => null),
        api.platformHub.events(eventFilter || undefined).catch(() => ({ events: [] })),
      ]);
      if (healthData) setHealth(healthData as PlatformHealth);
      if (statsData) setStats(statsData as PlatformStats);
      if (eventsData) setEvents((eventsData as { events: PlatformEvent[] }).events || []);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [eventFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadData]);

  const handleStart = async () => {
    try {
      setStarting(true);
      await api.platformHub.start();
      await loadData();
    } catch {
      // fail silently
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    try {
      setStopping(true);
      await api.platformHub.stop();
      await loadData();
    } catch {
      // fail silently
    } finally {
      setStopping(false);
    }
  };

  const handleConfigUpdate = async () => {
    try {
      await api.platformHub.updateConfig(configForm);
      await loadData();
      setConfigOpen(false);
    } catch {
      // fail silently
    }
  };

  const loadConfig = async () => {
    try {
      const config = await api.platformHub.config();
      setConfigForm(config as typeof configForm);
      setConfigOpen(true);
    } catch {
      // fail silently
    }
  };

  const formatUptime = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
    return `${Math.round(seconds / 86400)}d`;
  };

  if (loading && !health) {
    return (
      <div className="panel-loading">
        <div className="spinner" />
        <p>Loading platform status...</p>
      </div>
    );
  }

  return (
    <div className="panel">
      {/* Header */}
      <div className="panel-header">
        <h2>Platform Hub</h2>
        <div className="panel-header-actions">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Auto-refresh</span>
          </label>
          <button className="btn-icon" onClick={loadData} title="Refresh">
            🔄
          </button>
          {health?.is_running ? (
            <button
              className="btn btn-danger"
              onClick={handleStop}
              disabled={stopping}
            >
              {stopping ? 'Stopping...' : 'Stop Hub'}
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={handleStart}
              disabled={starting}
            >
              {starting ? 'Starting...' : 'Start Hub'}
            </button>
          )}
          <button className="btn btn-secondary" onClick={loadConfig}>
            Config
          </button>
        </div>
      </div>

      {/* Health Overview */}
      {health && (
        <div className="platform-health-overview">
          <div className="health-card" style={{ borderLeft: `4px solid ${STATUS_COLORS[health.overall] || '#9ca3af'}` }}>
            <div className="health-card-header">
              <span className="health-status-badge" style={{ background: STATUS_COLORS[health.overall] || '#9ca3af' }}>
                {health.overall.toUpperCase()}
              </span>
              <span className="health-uptime">
                Uptime: {formatUptime(health.uptime_seconds)}
              </span>
            </div>
            <div className="health-metrics">
              <div className="health-metric">
                <span className="metric-value">{health.subsystem_count.running}</span>
                <span className="metric-label">Running</span>
              </div>
              <div className="health-metric">
                <span className="metric-value">{health.subsystem_count.degraded}</span>
                <span className="metric-label">Degraded</span>
              </div>
              <div className="health-metric">
                <span className="metric-value">{health.subsystem_count.error}</span>
                <span className="metric-label">Errors</span>
              </div>
              <div className="health-metric">
                <span className="metric-value">{health.subsystem_count.stopped}</span>
                <span className="metric-label">Stopped</span>
              </div>
            </div>
            <div className="health-ratio-bar">
              <div
                className="health-ratio-fill"
                style={{
                  width: `${health.health_ratio * 100}%`,
                  background: health.health_ratio >= 1 ? '#10b981' : health.health_ratio >= 0.7 ? '#f59e0b' : '#ef4444',
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Subsystems Grid */}
      {health && (
        <div className="panel-section">
          <h3>Subsystems</h3>
          <div className="subsystem-grid">
            {Object.entries(health.subsystems).map(([name, info]) => (
              <div
                key={name}
                className={`subsystem-card subsystem-${info.status}`}
              >
                <div className="subsystem-card-header">
                  <span
                    className="subsystem-status-dot"
                    style={{ background: STATUS_COLORS[info.status] || '#9ca3af' }}
                  />
                  <span className="subsystem-name">
                    {name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </span>
                  <span
                    className="subsystem-status-chip"
                    style={{ background: STATUS_COLORS[info.status] || '#9ca3af' }}
                  >
                    {info.status}
                  </span>
                </div>
                <div className="subsystem-card-body">
                  {info.started_at && (
                    <div className="subsystem-detail">
                      <span>Started:</span>
                      <span>{new Date(info.started_at).toLocaleTimeString()}</span>
                    </div>
                  )}
                  {info.error_count > 0 && (
                    <div className="subsystem-detail error">
                      <span>Errors:</span>
                      <span>{info.error_count}</span>
                    </div>
                  )}
                  {info.last_error && (
                    <div className="subsystem-detail error-message">
                      <span>Last Error:</span>
                      <span className="truncate">{info.last_error}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Events */}
      <div className="panel-section">
        <div className="panel-section-header">
          <h3>Platform Events</h3>
          <input
            type="text"
            className="search-input"
            placeholder="Filter by event type..."
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
          />
        </div>
        <div className="events-list">
          {events.length === 0 && (
            <div className="empty-state">No events recorded</div>
          )}
          {events.map((event) => (
            <div
              key={event.id}
              className={`event-item event-${event.severity}`}
              style={{ borderLeftColor: STATUS_COLORS[event.severity] || '#9ca3af' }}
            >
              <div className="event-item-header">
                <span className="event-severity">
                  {SEVERITY_ICONS[event.severity] || '📌'} {event.severity}
                </span>
                <span className="event-time">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="event-item-body">
                <span className="event-type">{event.event_type}</span>
                <span className="event-source">from {event.source}</span>
              </div>
              {event.data && Object.keys(event.data).length > 0 && (
                <pre className="event-data">
                  {JSON.stringify(event.data, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="panel-section">
          <h3>Statistics</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{stats.events.total}</span>
              <span className="stat-label">Total Events</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.listener_count}</span>
              <span className="stat-label">Event Listeners</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.subsystem_count}</span>
              <span className="stat-label">Subsystems</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{formatUptime(stats.uptime_seconds)}</span>
              <span className="stat-label">Uptime</span>
            </div>
          </div>
        </div>
      )}

      {/* Config Modal */}
      {configOpen && (
        <div className="modal-overlay" onClick={() => setConfigOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Platform Hub Configuration</h2>
            <div className="form-group">
              <label>Auto Restart Subsystems</label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={configForm.auto_restart_subsystems}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, auto_restart_subsystems: e.target.checked })
                  }
                />
                <span>Enable automatic restart of failed subsystems</span>
              </label>
            </div>
            <div className="form-group">
              <label>Health Check Interval (ms)</label>
              <input
                type="number"
                value={configForm.health_check_interval_ms}
                onChange={(e) =>
                  setConfigForm({ ...configForm, health_check_interval_ms: Number(e.target.value) })
                }
                min={5000}
                max={300000}
              />
            </div>
            <div className="form-group">
              <label>Max Subsystem Restarts</label>
              <input
                type="number"
                value={configForm.max_subsystem_restarts}
                onChange={(e) =>
                  setConfigForm({ ...configForm, max_subsystem_restarts: Number(e.target.value) })
                }
                min={1}
                max={10}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setConfigOpen(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleConfigUpdate}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};