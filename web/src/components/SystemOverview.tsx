import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { TabView } from '../types';

interface SubsystemInfo {
  name: string;
  label: string;
  tabId: TabView | null;
  status: 'online' | 'offline' | 'degraded' | 'unknown';
  lastHeartbeat: string | null;
  uptime: number;
  description: string;
}

interface SystemEvent {
  id: string;
  type: string;
  source: string;
  data: Record<string, unknown>;
  timestamp: string;
  severity: string;
}

interface HealthCheckRecord {
  time: string;
  score: number;
  status: string;
}

const SUBSYSTEM_DEFINITIONS: { name: string; label: string; tabId: TabView | null; description: string }[] = [
  { name: 'agent', label: 'Agent Engine', tabId: 'chat', description: 'Core agent conversation and reasoning engine' },
  { name: 'memory', label: 'Memory System', tabId: 'memory', description: 'Short-term and long-term memory storage' },
  { name: 'kg', label: 'Knowledge Graph', tabId: 'kgraph', description: 'Entity-relationship knowledge network' },
  { name: 'mcp', label: 'MCP Servers', tabId: 'mcp', description: 'Model Context Protocol integrations' },
  { name: 'dream', label: 'Dream Engine', tabId: 'dream', description: 'Background memory consolidation cycles' },
  { name: 'proactive', label: 'Proactive Discovery', tabId: 'proactive', description: 'Autonomous task discovery engine' },
  { name: 'gateway', label: 'Gateway', tabId: 'gateway', description: 'Multi-platform messaging gateway' },
  { name: 'daemon', label: 'Daemon', tabId: 'daemon', description: 'Background agent execution daemon' },
  { name: 'swarm', label: 'Swarm Engine', tabId: 'swarm', description: 'Multi-agent swarm coordination' },
  { name: 'guard', label: 'Guard', tabId: 'guard', description: 'Safety and monitoring system' },
  { name: 'pulse', label: 'Pulse Monitor', tabId: 'pulse', description: 'System health and anomaly detection' },
  { name: 'nexus', label: 'Nexus Hub', tabId: 'nexus', description: 'Cross-platform coordination hub' },
  { name: 'forge', label: 'Forge', tabId: 'forge', description: 'Skill creation and evolution engine' },
  { name: 'scheduler', label: 'Scheduler', tabId: 'scheduler', description: 'Cron-based task scheduling' },
  { name: 'studio', label: 'Studio', tabId: 'studio', description: 'Persistent project workspaces' },
  { name: 'workflow', label: 'Workflow', tabId: 'workflow', description: 'Task state machine workflow engine' },
  { name: 'trajectory', label: 'Trajectory', tabId: 'trajectory', description: 'Execution trace recording and compression' },
  { name: 'collaboration', label: 'Collaboration', tabId: 'collaboration', description: 'Multi-agent collaboration forum' },
  { name: 'learning', label: 'Learning', tabId: 'learning', description: 'Self-improvement and pattern learning' },
  { name: 'evolution', label: 'Evolution', tabId: 'evolution', description: 'Agent evolution and pathway optimization' },
];

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function formatTimeAgo(isoString: string | null): string {
  if (!isoString) return 'Never';
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// Simple text-based architecture diagram
function ArchitectureDiagram() {
  const layers = [
    { name: 'User Interface', components: ['Web UI', 'CLI', 'API Gateway'], color: '#3b82f6' },
    { name: 'Orchestration', components: ['Agent Engine', 'Nexus Hub', 'Swarm Engine'], color: '#8b5cf6' },
    { name: 'Processing', components: ['Memory', 'KG', 'Forge', 'Trajectory'], color: '#06b6d4' },
    { name: 'Background', components: ['Daemon', 'Dream', 'Proactive', 'Scheduler'], color: '#f59e0b' },
    { name: 'Integration', components: ['MCP', 'Gateway', 'Pulse', 'Guard'], color: '#22c55e' },
  ];

  return (
    <div className="architecture-diagram">
      {layers.map((layer, li) => (
        <div key={layer.name} className={`arch-layer arch-layer-${li}`}>
          <div className="arch-layer-label" style={{ borderColor: layer.color, color: layer.color }}>
            {layer.name}
          </div>
          <div className="arch-layer-components">
            {layer.components.map((comp) => (
              <div key={comp} className="arch-component" style={{ borderColor: layer.color }}>
                {comp}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export const SystemOverview: React.FC<{ onNavigate?: (tab: TabView) => void }> = ({ onNavigate }) => {
  const [subsystems, setSubsystems] = useState<SubsystemInfo[]>([]);
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [healthHistory, setHealthHistory] = useState<HealthCheckRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>(null);
  const [resourceUsage, setResourceUsage] = useState<{ memory: string; storage: string; connections: number }>({
    memory: 'N/A',
    storage: 'N/A',
    connections: 0,
  });

  const loadData = useCallback(async () => {
    try {
      const [ov, ph, platformEvents] = await Promise.all([
        api.system.overview(),
        api.platformHub.health().catch(() => null),
        api.platformHub.events(undefined, 50).catch(() => null),
      ]);

      setOverview(ov);

      // Build subsystem status from platform health
      const subsysList: SubsystemInfo[] = [];
      if (ph?.subsystems) {
        Object.entries(ph.subsystems).forEach(([name, info]: [string, any]) => {
          const def = SUBSYSTEM_DEFINITIONS.find((d) => d.name === name);
          subsysList.push({
            name,
            label: def?.label || name,
            tabId: def?.tabId || null,
            status: info.status || 'unknown',
            lastHeartbeat: info.last_heartbeat || null,
            uptime: info.uptime_seconds || 0,
            description: def?.description || `Subsystem: ${name}`,
          });
        });
      } else {
        // Fallback: create entries from main overview
        SUBSYSTEM_DEFINITIONS.forEach((def) => {
          subsysList.push({
            name: def.name,
            label: def.label,
            tabId: def.tabId,
            status: 'unknown',
            lastHeartbeat: null,
            uptime: 0,
            description: def.description,
          });
        });
      }

      setSubsystems(subsysList);

      // Resource usage from overview
      setResourceUsage({
        memory: ph?.memory_usage ? `${(ph.memory_usage / 1024 / 1024).toFixed(1)} MB` : 'N/A',
        storage: ov?.memories ? `${ov.memories.total} records` : 'N/A',
        connections: ov?.agents?.active || 0,
      });

      // Events timeline
      if (platformEvents?.events) {
        setEvents(
          platformEvents.events
            .slice(0, 50)
            .map((e: any) => ({
              id: e.id || `evt-${Date.now()}-${Math.random()}`,
              type: e.type || e.event_type || 'system',
              source: e.source || 'platform',
              data: e.data || {},
              timestamp: e.timestamp || new Date().toISOString(),
              severity: e.severity || (e.type === 'error' ? 'error' : e.type === 'warning' ? 'warning' : 'info'),
            }))
        );
      }

      // Health history: store current data point
      const score = ph?.health_ratio ? Math.round(ph.health_ratio * 100) : 75;
      const status = ph?.overall || 'unknown';
      setHealthHistory((prev) => {
        const updated = [
          ...prev,
          { time: new Date().toISOString(), score, status },
        ];
        return updated.slice(-24);
      });
    } catch (err) {
      console.error('System overview load error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const statusColor = (status: string) => {
    switch (status) {
      case 'online': return '#22c55e';
      case 'degraded': return '#f59e0b';
      case 'offline': return '#ef4444';
      default: return '#94a3b8';
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case 'online': return 'Online';
      case 'degraded': return 'Degraded';
      case 'offline': return 'Offline';
      default: return 'Unknown';
    }
  };

  const onlineCount = subsystems.filter((s) => s.status === 'online').length;
  const degradedCount = subsystems.filter((s) => s.status === 'degraded').length;
  const offlineCount = subsystems.filter((s) => s.status === 'offline').length;

  if (loading) {
    return (
      <div className="system-overview-panel">
        <div className="panel-loading">Loading system overview...</div>
      </div>
    );
  }

  return (
    <div className="system-overview-panel">
      <div className="system-overview-header">
        <h2>System Overview</h2>
        <span className="system-overview-version">
          {overview?.service || 'Buddy'} v{overview?.version || 'N/A'}
        </span>
        <button className="btn-sm" onClick={loadData}>
          Refresh
        </button>
      </div>

      {/* Architecture Diagram */}
      <div className="system-overview-section">
        <h3>System Architecture</h3>
        <ArchitectureDiagram />
      </div>

      {/* Module Status Grid */}
      <div className="system-overview-section">
        <div className="system-overview-section-header">
          <h3>Module Status</h3>
          <div className="module-status-summary">
            <span className="module-status-count online">{onlineCount} Online</span>
            <span className="module-status-count degraded">{degradedCount} Degraded</span>
            <span className="module-status-count offline">{offlineCount} Offline</span>
          </div>
        </div>
        <div className="module-grid">
          {subsystems.map((mod) => (
            <div
              key={mod.name}
              className={`module-card module-${mod.status}`}
              onClick={() => {
                if (mod.tabId && onNavigate) {
                  onNavigate(mod.tabId);
                }
              }}
              style={{ cursor: mod.tabId ? 'pointer' : 'default' }}
              title={mod.tabId ? `Navigate to ${mod.label}` : undefined}
            >
              <div className="module-card-header">
                <span
                  className="module-status-dot"
                  style={{ background: statusColor(mod.status) }}
                />
                <span className="module-name">{mod.label}</span>
                <span
                  className="module-status-chip"
                  style={{ background: statusColor(mod.status) }}
                >
                  {statusLabel(mod.status)}
                </span>
              </div>
              <div className="module-card-body">
                <span className="module-description">{mod.description}</span>
                <div className="module-details">
                  <span>Last heartbeat: {formatTimeAgo(mod.lastHeartbeat)}</span>
                  <span>Uptime: {formatUptime(mod.uptime)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resource Usage Overview */}
      <div className="system-overview-section">
        <h3>Resource Usage</h3>
        <div className="resource-usage-grid">
          <div className="resource-card">
            <span className="resource-value">{resourceUsage.memory}</span>
            <span className="resource-label">Memory Usage</span>
          </div>
          <div className="resource-card">
            <span className="resource-value">{resourceUsage.storage}</span>
            <span className="resource-label">Storage</span>
          </div>
          <div className="resource-card">
            <span className="resource-value">{resourceUsage.connections}</span>
            <span className="resource-label">Active Connections</span>
          </div>
          <div className="resource-card">
            <span className="resource-value">{overview?.tasks?.total || 0}</span>
            <span className="resource-label">Total Tasks</span>
          </div>
        </div>
      </div>

      {/* Health Check History */}
      <div className="system-overview-section">
        <h3>Health Check History (Last 24 checks)</h3>
        {healthHistory.length > 0 ? (
          <div className="health-history-chart">
            <div className="health-history-bars">
              {healthHistory.map((record, i) => (
                <div key={i} className="health-history-bar-container" title={`${new Date(record.time).toLocaleTimeString()}: ${record.score}% (${record.status})`}>
                  <div
                    className="health-history-bar"
                    style={{
                      height: `${record.score}%`,
                      background: record.score >= 70 ? '#22c55e' : record.score >= 40 ? '#f59e0b' : '#ef4444',
                    }}
                  />
                </div>
              ))}
            </div>
            <div className="health-history-labels">
              <span>Oldest</span>
              <span>Newest</span>
            </div>
          </div>
        ) : (
          <div className="panel-empty">No health check data yet. Data will accumulate over time.</div>
        )}
      </div>

      {/* Recent System Events Timeline */}
      <div className="system-overview-section">
        <h3>Recent Events</h3>
        {events.length > 0 ? (
          <div className="events-timeline">
            {events.slice(0, 50).map((event, i) => (
              <div key={event.id || i} className={`event-timeline-item event-${event.severity}`}>
                <div className="event-timeline-dot" style={{ background: statusColor(event.severity === 'error' ? 'offline' : event.severity) }} />
                <div className="event-timeline-content">
                  <div className="event-timeline-header">
                    <span className="event-timeline-type">{event.type}</span>
                    <span className="event-timeline-source">{event.source}</span>
                    <span className="event-timeline-time">{formatTimeAgo(event.timestamp)}</span>
                  </div>
                  {event.data && Object.keys(event.data).length > 0 && (
                    <pre className="event-timeline-data">
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="panel-empty">No recent events.</div>
        )}
      </div>
    </div>
  );
};