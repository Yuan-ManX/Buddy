import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface MeshStats {
  total_capabilities: number;
  total_providers: number;
  total_nodes: number;
  total_plans: number;
  domains_covered: number;
  uptime_seconds: number;
}

interface Capability {
  capability_id: string;
  name: string;
  description: string;
  domain: string;
  type: string;
  tags: string[];
  provider_id: string;
  status: string;
  created_at: string;
}

interface CompositionPlan {
  plan_id: string;
  name: string;
  description: string;
  capabilities: string[];
  status: string;
  created_at: string;
}

interface DomainCoverage {
  domain: string;
  capability_count: number;
  coverage_percentage: number;
}

interface MeshProvider {
  provider_id: string;
  name: string;
  type: string;
  capability_count: number;
  status: string;
}

interface MeshNode {
  node_id: string;
  name: string;
  address: string;
  status: string;
  provider_count: number;
  last_seen: string;
}

interface DiscoverResult {
  query: string;
  results: Capability[];
  total_found: number;
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

export const CapabilityMeshPanel: React.FC = () => {
  const toast = useToast();

  // ── State ──
  const [stats, setStats] = useState<MeshStats | null>(null);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [plans, setPlans] = useState<CompositionPlan[]>([]);
  const [domainCoverage, setDomainCoverage] = useState<DomainCoverage[]>([]);
  const [providers, setProviders] = useState<MeshProvider[]>([]);
  const [nodes, setNodes] = useState<MeshNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<
    'overview' | 'register' | 'discover' | 'capabilities' | 'plans' | 'domains' | 'providers' | 'nodes'
  >('overview');

  // Register form
  const [registerForm, setRegisterForm] = useState({
    name: '',
    description: '',
    domain: '',
    type: 'tool',
    tags: '',
  });
  const [registering, setRegistering] = useState(false);

  // Discover form
  const [discoverQuery, setDiscoverQuery] = useState('');
  const [discoverResult, setDiscoverResult] = useState<DiscoverResult | null>(null);
  const [discovering, setDiscovering] = useState(false);

  // ── Data Loading ──

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, cap, p, dc, prov, nd] = await Promise.all([
        request<MeshStats>('/capability-mesh/stats').catch(() => null),
        request<Capability[]>('/capability-mesh/capabilities').catch(() => []),
        request<CompositionPlan[]>('/capability-mesh/plans').catch(() => []),
        request<DomainCoverage[]>('/capability-mesh/domain-coverage').catch(() => []),
        request<MeshProvider[]>('/capability-mesh/providers').catch(() => []),
        request<MeshNode[]>('/capability-mesh/nodes').catch(() => []),
      ]);
      setStats(s);
      setCapabilities(Array.isArray(cap) ? cap : (cap as any)?.capabilities || []);
      setPlans(Array.isArray(p) ? p : (p as any)?.plans || []);
      setDomainCoverage(Array.isArray(dc) ? dc : (dc as any)?.coverage || []);
      setProviders(Array.isArray(prov) ? prov : (prov as any)?.providers || []);
      setNodes(Array.isArray(nd) ? nd : (nd as any)?.nodes || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load capability mesh data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Handlers ──

  const handleRegister = async () => {
    if (!registerForm.name.trim() || !registerForm.description.trim()) return;
    try {
      setRegistering(true);
      const tags = registerForm.tags
        ? registerForm.tags.split(',').map((t) => t.trim()).filter(Boolean)
        : [];
      await request('/capability-mesh/capabilities', {
        method: 'POST',
        body: JSON.stringify({
          name: registerForm.name,
          description: registerForm.description,
          domain: registerForm.domain,
          type: registerForm.type,
          tags,
        }),
      });
      toast.success(`Capability "${registerForm.name}" registered successfully`);
      setRegisterForm({ name: '', description: '', domain: '', type: 'tool', tags: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRegistering(false);
    }
  };

  const handleDiscover = async () => {
    if (!discoverQuery.trim()) return;
    try {
      setDiscovering(true);
      const result = await request<DiscoverResult>('/capability-mesh/discover', {
        method: 'POST',
        body: JSON.stringify({ query: discoverQuery }),
      });
      setDiscoverResult(result);
      toast.success(`Found ${result.total_found || (result.results?.length || 0)} capabilities`);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setDiscovering(false);
    }
  };

  // ── Helpers ──

  const typeColors: Record<string, string> = {
    tool: '#4f6ef7',
    skill: '#8b5cf6',
    model: '#22c55e',
    data: '#f59e0b',
    service: '#06b6d4',
    agent: '#ef4444',
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    available: '#22c55e',
    online: '#22c55e',
    inactive: '#9ca3af',
    offline: '#9ca3af',
    degraded: '#f59e0b',
    error: '#ef4444',
    draft: '#3b82f6',
  };

  const domainColors: Record<string, string> = {
    code: '#4f6ef7',
    data: '#22c55e',
    communication: '#8b5cf6',
    knowledge: '#f59e0b',
    automation: '#06b6d4',
    security: '#ef4444',
    media: '#ec4899',
  };

  // ── Loading State ──

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Capability Mesh</h2>
          <p className="panel-subtitle">Distributed capability discovery and composition mesh</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading capability mesh data...</span>
        </div>
      </div>
    );
  }

  // ── Main Render ──

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Capability Mesh</h2>
        <p className="panel-subtitle">Distributed capability registration, discovery, and composition</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_capabilities}</span>
              <span className="stat-label">Capabilities</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#4f6ef7' }}>{stats.total_providers}</span>
              <span className="stat-label">Providers</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.total_nodes}</span>
              <span className="stat-label">Nodes</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>{stats.total_plans}</span>
              <span className="stat-label">Plans</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.domains_covered}</span>
              <span className="stat-label">Domains</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'register', 'discover', 'capabilities', 'plans', 'domains', 'providers', 'nodes'] as const).map(
          (s) => (
            <button
              key={s}
              className={`forge-tab ${activeSection === s ? 'active' : ''}`}
              onClick={() => setActiveSection(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          )
        )}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Mesh Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Capabilities</span>
                <strong>{stats.total_capabilities}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Providers</span>
                <strong style={{ color: '#4f6ef7' }}>{stats.total_providers}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Nodes</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.total_nodes}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Composition Plans</span>
                <strong style={{ color: '#f59e0b' }}>{stats.total_plans}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Domains Covered</span>
                <strong style={{ color: '#22c55e' }}>{stats.domains_covered}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Uptime</span>
                <strong>{Math.floor(stats.uptime_seconds / 3600)}h {Math.floor((stats.uptime_seconds % 3600) / 60)}m</strong>
              </div>

              {/* Recent Capabilities */}
              <h3 style={{ marginTop: 24 }}>Recent Capabilities</h3>
              {capabilities.length === 0 ? (
                <div className="panel-empty">No capabilities registered yet</div>
              ) : (
                <div className="forge-skill-list">
                  {capabilities.slice(0, 5).map((cap) => (
                    <div key={cap.capability_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{cap.name}</div>
                        <span
                          className="dashboard-badge"
                          style={{
                            background: typeColors[cap.type] || '#666',
                            color: '#fff',
                          }}
                        >
                          {cap.type}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{cap.description}</div>
                        <div>
                          Domain: {cap.domain} | Status:{' '}
                          <span style={{ color: statusColors[cap.status] || '#9ca3af', fontWeight: 600 }}>
                            {cap.status}
                          </span>
                        </div>
                        {cap.tags && cap.tags.length > 0 && (
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                            {cap.tags.map((tag, idx) => (
                              <span
                                key={idx}
                                style={{
                                  padding: '2px 8px',
                                  background: '#e8eaf6',
                                  color: '#4f6ef7',
                                  borderRadius: 12,
                                  fontSize: '0.7rem',
                                }}
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
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
          <h3>Register New Capability</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={registerForm.name}
                onChange={(e) => setRegisterForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g., Code Analysis Engine"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={registerForm.description}
                onChange={(e) => setRegisterForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this capability does..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Domain</label>
                <input
                  type="text"
                  value={registerForm.domain}
                  onChange={(e) => setRegisterForm((f) => ({ ...f, domain: e.target.value }))}
                  placeholder="e.g., code, data, automation"
                />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select
                  value={registerForm.type}
                  onChange={(e) => setRegisterForm((f) => ({ ...f, type: e.target.value }))}
                >
                  <option value="tool">Tool</option>
                  <option value="skill">Skill</option>
                  <option value="model">Model</option>
                  <option value="data">Data</option>
                  <option value="service">Service</option>
                  <option value="agent">Agent</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                value={registerForm.tags}
                onChange={(e) => setRegisterForm((f) => ({ ...f, tags: e.target.value }))}
                placeholder="e.g., analysis, python, ml"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleRegister}
              disabled={registering || !registerForm.name.trim() || !registerForm.description.trim()}
            >
              {registering ? 'Registering...' : 'Register Capability'}
            </button>
          </div>
        </div>
      )}

      {/* ── Discover Section ── */}
      {activeSection === 'discover' && (
        <div className="dashboard-section">
          <h3>Discover Capabilities</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              type="text"
              value={discoverQuery}
              onChange={(e) => setDiscoverQuery(e.target.value)}
              placeholder="Search by name, domain, type, or tags..."
              style={{ flex: 1 }}
            />
            <button
              className="btn-primary"
              onClick={handleDiscover}
              disabled={discovering || !discoverQuery.trim()}
              style={{ background: '#8b5cf6' }}
            >
              {discovering ? 'Searching...' : 'Search'}
            </button>
          </div>

          {discoverResult && (
            <>
              <div style={{ marginBottom: 12, color: '#6b7280', fontSize: '0.9rem' }}>
                Found {discoverResult.total_found || discoverResult.results?.length || 0} results for "{discoverResult.query}"
              </div>
              {discoverResult.results && discoverResult.results.length > 0 ? (
                <div className="forge-skill-list">
                  {discoverResult.results.map((cap) => (
                    <div key={cap.capability_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{cap.name}</div>
                        <span
                          className="dashboard-badge"
                          style={{
                            background: typeColors[cap.type] || '#666',
                            color: '#fff',
                          }}
                        >
                          {cap.type}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{cap.description}</div>
                        <div>Domain: {cap.domain} | Provider: {cap.provider_id}</div>
                        {cap.tags && cap.tags.length > 0 && (
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                            {cap.tags.map((tag, idx) => (
                              <span
                                key={idx}
                                style={{
                                  padding: '2px 8px',
                                  background: '#e8eaf6',
                                  color: '#4f6ef7',
                                  borderRadius: 12,
                                  fontSize: '0.7rem',
                                }}
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No capabilities found matching your query</div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Capabilities Section ── */}
      {activeSection === 'capabilities' && (
        <div className="dashboard-section">
          <h3>Registered Capabilities ({capabilities.length})</h3>

          {capabilities.length === 0 ? (
            <div className="panel-empty">No capabilities registered yet. Go to the Register tab to add one.</div>
          ) : (
            <div className="forge-skill-list">
              {capabilities.map((cap) => (
                <div key={cap.capability_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{cap.name}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: typeColors[cap.type] || '#666',
                        color: '#fff',
                      }}
                    >
                      {cap.type}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{cap.description}</div>
                    <div>
                      Domain: {cap.domain} | Status:{' '}
                      <span style={{ color: statusColors[cap.status] || '#9ca3af', fontWeight: 600 }}>
                        {cap.status}
                      </span>
                    </div>
                    <div>Provider: {cap.provider_id}</div>
                    <div>Created: {new Date(cap.created_at).toLocaleString()}</div>
                    {cap.tags && cap.tags.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                        {cap.tags.map((tag, idx) => (
                          <span
                            key={idx}
                            style={{
                              padding: '2px 8px',
                              background: '#e8eaf6',
                              color: '#4f6ef7',
                              borderRadius: 12,
                              fontSize: '0.7rem',
                            }}
                          >
                            {tag}
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

      {/* ── Plans Section ── */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <h3>Composition Plans ({plans.length})</h3>

          {plans.length === 0 ? (
            <div className="panel-empty">No composition plans defined</div>
          ) : (
            <div className="forge-skill-list">
              {plans.map((plan) => (
                <div key={plan.plan_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{plan.name}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: statusColors[plan.status] || '#3b82f6',
                        color: '#fff',
                      }}
                    >
                      {plan.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{plan.description}</div>
                    <div>
                      Capabilities: {plan.capabilities?.length || 0}
                    </div>
                    {plan.capabilities && plan.capabilities.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                        {plan.capabilities.map((capId, idx) => (
                          <span
                            key={idx}
                            style={{
                              padding: '2px 8px',
                              background: '#fef3c7',
                              color: '#92400e',
                              borderRadius: 12,
                              fontSize: '0.7rem',
                              fontFamily: 'monospace',
                            }}
                          >
                            {capId}
                          </span>
                        ))}
                      </div>
                    )}
                    <div>Created: {new Date(plan.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Domains Section ── */}
      {activeSection === 'domains' && (
        <div className="dashboard-section">
          <h3>Domain Coverage</h3>

          {domainCoverage.length === 0 ? (
            <div className="panel-empty">No domain coverage data available</div>
          ) : (
            <div className="forge-skill-list">
              {domainCoverage.map((dc) => (
                <div key={dc.domain} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ color: domainColors[dc.domain] || '#374151' }}>
                      {dc.domain}
                    </div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: dc.coverage_percentage >= 80 ? '#22c55e' : dc.coverage_percentage >= 50 ? '#f59e0b' : '#ef4444',
                        color: '#fff',
                      }}
                    >
                      {dc.coverage_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                        <span style={{ fontSize: '0.85rem', color: '#6b7280', minWidth: 80 }}>
                          Coverage
                        </span>
                        <div
                          style={{
                            flex: 1,
                            height: 8,
                            background: '#e5e7eb',
                            borderRadius: 4,
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${Math.min(dc.coverage_percentage, 100)}%`,
                              height: '100%',
                              background:
                                dc.coverage_percentage >= 80
                                  ? '#22c55e'
                                  : dc.coverage_percentage >= 50
                                  ? '#f59e0b'
                                  : '#ef4444',
                              borderRadius: 4,
                              transition: 'width 0.3s ease',
                            }}
                          />
                        </div>
                      </div>
                    </div>
                    <div>Capabilities: {dc.capability_count}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Providers Section ── */}
      {activeSection === 'providers' && (
        <div className="dashboard-section">
          <h3>Mesh Providers ({providers.length})</h3>

          {providers.length === 0 ? (
            <div className="panel-empty">No providers registered</div>
          ) : (
            <div className="forge-skill-list">
              {providers.map((provider) => (
                <div key={provider.provider_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{provider.name}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: typeColors[provider.type] || '#4f6ef7',
                        color: '#fff',
                      }}
                    >
                      {provider.type}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      Capabilities: {provider.capability_count} | Status:{' '}
                      <span style={{ color: statusColors[provider.status] || '#9ca3af', fontWeight: 600 }}>
                        {provider.status}
                      </span>
                    </div>
                    <div>ID: {provider.provider_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Nodes Section ── */}
      {activeSection === 'nodes' && (
        <div className="dashboard-section">
          <h3>Mesh Nodes ({nodes.length})</h3>

          {nodes.length === 0 ? (
            <div className="panel-empty">No mesh nodes connected</div>
          ) : (
            <div className="forge-skill-list">
              {nodes.map((node) => (
                <div key={node.node_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{node.name}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: statusColors[node.status] || '#9ca3af',
                        color: '#fff',
                      }}
                    >
                      {node.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{node.address}</div>
                    <div>Providers: {node.provider_count}</div>
                    <div>Last Seen: {new Date(node.last_seen).toLocaleString()}</div>
                    <div>ID: {node.node_id}</div>
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

export default CapabilityMeshPanel;