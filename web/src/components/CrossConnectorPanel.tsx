import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface CrossConnection {
  connection_id: string;
  name: string;
  source_system: string;
  target_system: string;
  protocol: string;
  status: string;
  schema_mappings: SchemaMapping[];
  created_at: string;
  updated_at: string;
}

interface SchemaMapping {
  mapping_id: string;
  source_field: string;
  target_field: string;
  transform: string;
  required: boolean;
}

interface CrossEvent {
  event_id: string;
  connection_id: string;
  event_type: string;
  source: string;
  target: string;
  payload: string;
  status: string;
  timestamp: string;
}

interface CrossRequest {
  request_id: string;
  connection_id: string;
  method: string;
  path: string;
  status: string;
  duration_ms: number;
  response_code: number;
  timestamp: string;
}

interface CrossConnectorStats {
  total_connections: number;
  active_connections: number;
  total_events: number;
  total_requests: number;
  total_mappings: number;
  average_latency_ms: number;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const CrossConnectorPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<CrossConnectorStats | null>(null);
  const [connections, setConnections] = useState<CrossConnection[]>([]);
  const [events, setEvents] = useState<CrossEvent[]>([]);
  const [requests, setRequests] = useState<CrossRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'register' | 'connections' | 'events' | 'requests'>('overview');

  // Register form
  const [registerForm, setRegisterForm] = useState({
    name: '',
    source_system: '',
    target_system: '',
    protocol: 'http',
    mappings: '',
  });
  const [registering, setRegistering] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, c, e, r] = await Promise.all([
        request<CrossConnectorStats>('/cross-connector/stats').catch(() => null),
        request<CrossConnection[]>('/cross-connector/connections').catch(() => []),
        request<CrossEvent[]>('/cross-connector/events').catch(() => []),
        request<CrossRequest[]>('/cross-connector/events').catch(() => []),
      ]);
      setStats(s);
      setConnections(Array.isArray(c) ? c : (c as any)?.connections || []);
      setEvents(Array.isArray(e) ? e : (e as any)?.events || []);
      setRequests(Array.isArray(r) ? r : (r as any)?.requests || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cross connector data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRegister = async () => {
    if (!registerForm.name.trim() || !registerForm.source_system.trim() || !registerForm.target_system.trim()) return;
    try {
      setRegistering(true);
      let mappings: SchemaMapping[] | undefined;
      if (registerForm.mappings.trim()) {
        try {
          mappings = JSON.parse(registerForm.mappings);
        } catch {
          toast.error('Invalid JSON format for mappings');
          setRegistering(false);
          return;
        }
      }
      const result = await request<any>('/cross-connector/connections', {
        method: 'POST',
        body: JSON.stringify({
          name: registerForm.name,
          source_system: registerForm.source_system,
          target_system: registerForm.target_system,
          protocol: registerForm.protocol,
          mappings: mappings || undefined,
        }),
      });
      toast.success(result.message || 'Connection registered successfully');
      setRegisterForm({ name: '', source_system: '', target_system: '', protocol: 'http', mappings: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRegistering(false);
    }
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    connected: '#22c55e',
    healthy: '#22c55e',
    degraded: '#f59e0b',
    disconnected: '#9ca3af',
    error: '#ef4444',
    failed: '#ef4444',
    pending: '#f59e0b',
    processing: '#3b82f6',
    success: '#22c55e',
    delivered: '#22c55e',
  };

  const protocolColors: Record<string, string> = {
    http: '#3b82f6',
    grpc: '#8b5cf6',
    websocket: '#22c55e',
    mqtt: '#f59e0b',
    amqp: '#ef4444',
    kafka: '#06b6d4',
    custom: '#9ca3af',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Cross Connector</h2>
          <p className="panel-subtitle">Connect and bridge between systems and services</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading cross connector data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Cross Connector</h2>
        <p className="panel-subtitle">Register connections, manage schema mappings, and monitor cross-system events</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_connections}</span>
              <span className="stat-label">Connections</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_connections}</span>
              <span className="stat-label">Active</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.total_events}</span>
              <span className="stat-label">Events</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.total_requests}</span>
              <span className="stat-label">Requests</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>{stats.total_mappings}</span>
              <span className="stat-label">Mappings</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'register', 'connections', 'events', 'requests'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Connector Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Connections</span>
                <strong>{stats.total_connections}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Active Connections</span>
                <strong style={{ color: '#22c55e' }}>{stats.active_connections}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Events</span>
                <strong style={{ color: '#3b82f6' }}>{stats.total_events}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Requests</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.total_requests}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Mappings</span>
                <strong style={{ color: '#f59e0b' }}>{stats.total_mappings}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Avg Latency</span>
                <strong>{stats.average_latency_ms?.toFixed(1)}ms</strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Connections</h3>
              {connections.length === 0 ? (
                <div className="panel-empty">No connections registered yet</div>
              ) : (
                <div className="forge-skill-list">
                  {connections.slice(0, 5).map(conn => (
                    <div key={conn.connection_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{conn.name}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[conn.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {conn.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>
                          {conn.source_system}
                          <span style={{ margin: '0 6px', color: '#9ca3af' }}>→</span>
                          {conn.target_system}
                        </div>
                        <div>
                          Protocol:{' '}
                          <span style={{
                            color: protocolColors[conn.protocol] || '#9ca3af',
                            fontWeight: 600,
                          }}>
                            {conn.protocol}
                          </span>
                          {' '}| Mappings: {conn.schema_mappings?.length || 0}
                        </div>
                        <div>Created: {new Date(conn.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <h3 style={{ marginTop: 24 }}>Recent Events</h3>
              {events.length === 0 ? (
                <div className="panel-empty">No events recorded yet</div>
              ) : (
                <div className="forge-skill-list">
                  {events.slice(0, 5).map(evt => (
                    <div key={evt.event_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{evt.event_type}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[evt.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {evt.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>
                          {evt.source}
                          <span style={{ margin: '0 6px', color: '#9ca3af' }}>→</span>
                          {evt.target}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: 4 }}>
                          {evt.payload?.substring(0, 150)}{evt.payload?.length > 150 ? '...' : ''}
                        </div>
                        <div>Timestamp: {new Date(evt.timestamp).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Register Section ── */}
      {activeSection === 'register' && (
        <div className="dashboard-section">
          <h3>Register Connection</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Connection Name</label>
              <input
                type="text"
                value={registerForm.name}
                onChange={e => setRegisterForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Cross-Connection"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Source System</label>
                <input
                  type="text"
                  value={registerForm.source_system}
                  onChange={e => setRegisterForm(f => ({ ...f, source_system: e.target.value }))}
                  placeholder="e.g., service_a, database_1"
                />
              </div>
              <div className="form-group">
                <label>Target System</label>
                <input
                  type="text"
                  value={registerForm.target_system}
                  onChange={e => setRegisterForm(f => ({ ...f, target_system: e.target.value }))}
                  placeholder="e.g., service_b, database_2"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Protocol</label>
              <select
                value={registerForm.protocol}
                onChange={e => setRegisterForm(f => ({ ...f, protocol: e.target.value }))}
              >
                <option value="http">HTTP/REST</option>
                <option value="grpc">gRPC</option>
                <option value="websocket">WebSocket</option>
                <option value="mqtt">MQTT</option>
                <option value="amqp">AMQP</option>
                <option value="kafka">Kafka</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div className="form-group">
              <label>Schema Mappings (JSON array)</label>
              <textarea
                rows={5}
                value={registerForm.mappings}
                onChange={e => setRegisterForm(f => ({ ...f, mappings: e.target.value }))}
                placeholder={`[
  {"source_field": "user_id", "target_field": "id", "transform": "direct", "required": true},
  {"source_field": "full_name", "target_field": "name", "transform": "direct", "required": true}
]`}
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleRegister}
              disabled={registering || !registerForm.name.trim() || !registerForm.source_system.trim() || !registerForm.target_system.trim()}
            >
              {registering ? 'Registering...' : 'Register Connection'}
            </button>
          </div>
        </div>
      )}

      {/* ── Connections Section ── */}
      {activeSection === 'connections' && (
        <div className="dashboard-section">
          <h3>Registered Connections ({connections.length})</h3>
          {connections.length === 0 ? (
            <div className="panel-empty">No connections registered yet. Go to the Register tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {connections.map(conn => (
                <div key={conn.connection_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{conn.name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[conn.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {conn.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div style={{ fontSize: '0.95rem', marginBottom: 4 }}>
                      <strong>{conn.source_system}</strong>
                      <span style={{ margin: '0 8px', color: '#9ca3af', fontSize: '1.2rem' }}>→</span>
                      <strong>{conn.target_system}</strong>
                    </div>
                    <div>
                      Protocol:{' '}
                      <span style={{
                        color: protocolColors[conn.protocol] || '#9ca3af',
                        fontWeight: 600,
                      }}>
                        {conn.protocol}
                      </span>
                    </div>

                    {conn.schema_mappings && conn.schema_mappings.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <strong>Schema Mappings ({conn.schema_mappings.length}):</strong>
                        <div style={{
                          marginTop: 4,
                          background: '#f9fafb',
                          borderRadius: 6,
                          padding: 8,
                          maxHeight: 200,
                          overflow: 'auto',
                        }}>
                          <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
                            <thead>
                              <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                                <th style={{ textAlign: 'left', padding: '4px 8px', color: '#6b7280' }}>Source</th>
                                <th style={{ textAlign: 'left', padding: '4px 8px', color: '#6b7280' }}>Target</th>
                                <th style={{ textAlign: 'left', padding: '4px 8px', color: '#6b7280' }}>Transform</th>
                                <th style={{ textAlign: 'center', padding: '4px 8px', color: '#6b7280' }}>Req</th>
                              </tr>
                            </thead>
                            <tbody>
                              {conn.schema_mappings.map((m, idx) => (
                                <tr key={m.mapping_id || idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                                  <td style={{ padding: '4px 8px', color: '#4f6ef7' }}>{m.source_field}</td>
                                  <td style={{ padding: '4px 8px', color: '#22c55e' }}>{m.target_field}</td>
                                  <td style={{ padding: '4px 8px' }}>{m.transform}</td>
                                  <td style={{ padding: '4px 8px', textAlign: 'center' }}>
                                    {m.required ? '✓' : '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    <div style={{ marginTop: 4 }}>
                      Created: {new Date(conn.created_at).toLocaleString()}
                    </div>
                    <div>Updated: {new Date(conn.updated_at).toLocaleString()}</div>
                    <div>Connection ID: {conn.connection_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Events Section ── */}
      {activeSection === 'events' && (
        <div className="dashboard-section">
          <h3>Cross-System Events ({events.length})</h3>
          {events.length === 0 ? (
            <div className="panel-empty">No events recorded yet</div>
          ) : (
            <div className="forge-skill-list">
              {events.map(evt => (
                <div key={evt.event_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{evt.event_type}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[evt.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {evt.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div style={{ fontSize: '0.9rem', marginBottom: 4 }}>
                      <strong>{evt.source}</strong>
                      <span style={{ margin: '0 6px', color: '#9ca3af' }}>→</span>
                      <strong>{evt.target}</strong>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: 4, maxHeight: 60, overflow: 'hidden' }}>
                      {evt.payload?.substring(0, 200)}{evt.payload?.length > 200 ? '...' : ''}
                    </div>
                    <div>Connection: {evt.connection_id}</div>
                    <div>Timestamp: {new Date(evt.timestamp).toLocaleString()}</div>
                    <div>Event ID: {evt.event_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Requests Section ── */}
      {activeSection === 'requests' && (
        <div className="dashboard-section">
          <h3>Cross-System Requests ({requests.length})</h3>
          {requests.length === 0 ? (
            <div className="panel-empty">No requests recorded yet</div>
          ) : (
            <div className="forge-skill-list">
              {requests.map(req => (
                <div key={req.request_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 6px',
                        background: req.method === 'GET' ? '#22c55e' : req.method === 'POST' ? '#3b82f6' : req.method === 'PUT' ? '#f59e0b' : '#ef4444',
                        color: '#fff',
                        borderRadius: 4,
                        fontSize: '0.75rem',
                        marginRight: 8,
                        fontWeight: 600,
                      }}>
                        {req.method}
                      </span>
                      {req.path}
                    </div>
                    <span className="dashboard-badge" style={{
                      background: req.response_code < 400 ? '#22c55e' : '#ef4444',
                      color: '#fff',
                    }}>
                      {req.response_code}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Duration: {req.duration_ms}ms | Status: {req.status}</div>
                    <div>Connection: {req.connection_id}</div>
                    <div>Timestamp: {new Date(req.timestamp).toLocaleString()}</div>
                    <div>Request ID: {req.request_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CrossConnectorPanel;