import React, { useState, useEffect } from 'react';

interface ProtocolStats {
  router: { processed_count: number; error_count: number; queue_size: number; registered_handlers: Record<string, number>; is_running: boolean };
  events: { total_events: number; subscriber_count: number; event_types: string[] };
  registry: { total_components: number; components_by_type: Record<string, number>; health_summary: any };
  synchronizer: { total_components: number; total_keys: number };
}

interface ComponentInfo {
  type: string;
  state: string;
  capabilities: string[];
  health: number;
}

export const ProtocolPanel: React.FC = () => {
  const [stats, setStats] = useState<ProtocolStats | null>(null);
  const [components, setComponents] = useState<Record<string, ComponentInfo>>({});
  const [eventStats, setEventStats] = useState<any>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [formData, setFormData] = useState({ component_id: '', component_type: '', capabilities: '', dependencies: '' });

  useEffect(() => {
    fetchStats();
    fetchComponents();
    fetchEventStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/protocol/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch protocol stats:', e); }
  };

  const fetchComponents = async () => {
    try {
      const res = await fetch('/api/protocol/components');
      const data = await res.json();
      setComponents(data.components || {});
    } catch (e) { console.error('Failed to fetch components:', e); }
  };

  const fetchEventStats = async () => {
    try {
      const res = await fetch('/api/protocol/events/stats');
      setEventStats(await res.json());
    } catch (e) { console.error('Failed to fetch event stats:', e); }
  };

  const registerComponent = async () => {
    try {
      await fetch('/api/protocol/register-component', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          capabilities: formData.capabilities.split(',').map(s => s.trim()).filter(Boolean),
          dependencies: formData.dependencies.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowRegister(false);
      setFormData({ component_id: '', component_type: '', capabilities: '', dependencies: '' });
      fetchStats();
      fetchComponents();
    } catch (e) { console.error('Failed to register:', e); }
  };

  const stateColor = (state: string) => {
    switch (state) {
      case 'active': case 'ready': return '#22c55e';
      case 'degraded': return '#f59e0b';
      case 'error': case 'offline': return '#ef4444';
      case 'initializing': return '#3b82f6';
      default: return '#94a3b8';
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Agent Protocol</h2>
        <span className="panel-subtitle">Unified communication layer</span>
      </div>

      <div className="panel-content">
        {/* Router Stats */}
        {stats?.router && (
          <div className="section">
            <h3>Message Router</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{stats.router.processed_count}</div>
                <div className="stat-label">Processed</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: stats.router.error_count > 0 ? '#ef4444' : '#22c55e' }}>
                  {stats.router.error_count}
                </div>
                <div className="stat-label">Errors</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{stats.router.queue_size}</div>
                <div className="stat-label">Queue</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: stats.router.is_running ? '#22c55e' : '#ef4444' }}>
                  {stats.router.is_running ? 'Running' : 'Stopped'}
                </div>
                <div className="stat-label">Status</div>
              </div>
            </div>
            {stats.router.registered_handlers && (
              <div className="chip-row">
                {Object.entries(stats.router.registered_handlers).map(([type, count]) => (
                  <span key={type} className="chip">{type}: {count}</span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Event Bus */}
        {eventStats && (
          <div className="section">
            <h3>Event Bus</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{eventStats.total_events}</div>
                <div className="stat-label">Total Events</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{eventStats.subscriber_count}</div>
                <div className="stat-label">Subscribers</div>
              </div>
            </div>
            {eventStats.event_types && (
              <div className="chip-row">
                {eventStats.event_types.map((t: string) => (
                  <span key={t} className="chip">{t}</span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Component Registry */}
        <div className="section">
          <div className="section-header">
            <h3>Components ({Object.keys(components).length})</h3>
            <button className="btn btn-secondary" onClick={() => setShowRegister(!showRegister)}>
              {showRegister ? 'Cancel' : 'Register'}
            </button>
          </div>

          {showRegister && (
            <div className="form-card">
              <input className="text-input" placeholder="Component ID" value={formData.component_id}
                onChange={e => setFormData({ ...formData, component_id: e.target.value })} />
              <input className="text-input" placeholder="Type" value={formData.component_type}
                onChange={e => setFormData({ ...formData, component_type: e.target.value })} />
              <input className="text-input" placeholder="Capabilities (comma-separated)" value={formData.capabilities}
                onChange={e => setFormData({ ...formData, capabilities: e.target.value })} />
              <input className="text-input" placeholder="Dependencies (comma-separated)" value={formData.dependencies}
                onChange={e => setFormData({ ...formData, dependencies: e.target.value })} />
              <button className="btn btn-primary" onClick={registerComponent}>Register</button>
            </div>
          )}

          <div className="list">
            {Object.entries(components).map(([cid, info]) => (
              <div key={cid} className="list-item">
                <div className="list-item-header">
                  <span className="list-item-name">{cid}</span>
                  <span className="badge" style={{ background: stateColor(info.state) }}>{info.state}</span>
                </div>
                <div className="list-item-meta">
                  <span>Type: {info.type}</span>
                  <span>Health: {(info.health * 100).toFixed(0)}%</span>
                </div>
                {info.capabilities.length > 0 && (
                  <div className="chip-row">
                    {info.capabilities.map((cap: string) => (
                      <span key={cap} className="chip chip-sm">{cap}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Registry Stats */}
        {stats?.registry && (
          <div className="section">
            <h3>Registry</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{stats.registry.total_components}</div>
                <div className="stat-label">Total</div>
              </div>
            </div>
            {stats.registry.components_by_type && (
              <div className="chip-row">
                {Object.entries(stats.registry.components_by_type).map(([type, count]) => (
                  <span key={type} className="chip">{type}: {count}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};