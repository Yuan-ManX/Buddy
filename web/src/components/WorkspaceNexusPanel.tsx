import React, { useState, useEffect, useCallback } from 'react';

const BASE_URL = '/api';
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try { const parsed = JSON.parse(body); message = parsed.detail || parsed.error || body; } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

type Tab = 'Overview' | 'Workspaces' | 'Connections' | 'Context' | 'Templates';

export const WorkspaceNexusPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('Overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview tab state
  const [stats, setStats] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);

  // Workspaces tab state
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [workspacesLoading, setWorkspacesLoading] = useState(false);
  const [newWorkspace, setNewWorkspace] = useState({ name: '', description: '', type: 'standard' });
  const [analytics, setAnalytics] = useState<any>(null);
  const [analyticsWsId, setAnalyticsWsId] = useState('');

  // Connections tab state
  const [connections, setConnections] = useState<any[]>([]);
  const [subsystem, setSubsystem] = useState('memory');
  const [subsystemId, setSubsystemId] = useState('');

  // Context tab state
  const [contextFlows, setContextFlows] = useState<any[]>([]);
  const [contextLoading, setContextLoading] = useState(false);
  const [newFlow, setNewFlow] = useState({ name: '', source: '', target: '', rules: '{}' });
  const [syncId, setSyncId] = useState('');

  // Templates tab state
  const [templates, setTemplates] = useState<any[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [newTemplate, setNewTemplate] = useState({ name: '', description: '', definition: '{}' });

  // Dark theme colors
  const colors = {
    bg: '#1a1a2e',
    card: '#16213e',
    border: '#2a2a4a',
    text: '#e0e0e0',
    accent: '#7c3aed',
    textSecondary: '#a0a0b0',
    green: '#10b981',
    red: '#ef4444',
    yellow: '#f59e0b',
    blue: '#3b82f6',
  };

  const inputStyle: React.CSSProperties = {
    padding: '8px 12px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    background: colors.bg,
    color: colors.text,
    fontSize: '14px',
    width: '100%',
    boxSizing: 'border-box',
  };

  const btnPrimary: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    background: colors.accent,
    color: '#fff',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  };

  const btnSecondary: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    background: colors.card,
    color: colors.text,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  };

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '8px 16px',
    border: 'none',
    borderRadius: '8px',
    background: activeTab === tab ? colors.accent : colors.card,
    color: activeTab === tab ? '#fff' : colors.textSecondary,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    transition: 'all 0.15s',
  });

  // Load overview data
  const loadOverview = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsData, summaryData] = await Promise.all([
        request<any>('/workspace-nexus/stats'),
        request<any>('/workspace-nexus/summary'),
      ]);
      setStats(statsData);
      setSummary(summaryData);
    } catch (err: any) {
      setError(err.message || 'Failed to load overview');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load workspaces
  const loadWorkspaces = useCallback(async () => {
    try {
      setWorkspacesLoading(true);
      const data = await request<any>('/workspace-nexus/workspaces');
      setWorkspaces(data.workspaces || data || []);
    } catch (err: any) {
      alert('Failed to load workspaces: ' + err.message);
    } finally {
      setWorkspacesLoading(false);
    }
  }, []);

  // Load context flows
  const loadContextFlows = useCallback(async () => {
    try {
      setContextLoading(true);
      const data = await request<any>('/workspace-nexus/context-flows');
      setContextFlows(data.flows || data || []);
    } catch (err: any) {
      alert('Failed to load context flows: ' + err.message);
    } finally {
      setContextLoading(false);
    }
  }, []);

  // Load templates
  const loadTemplates = useCallback(async () => {
    try {
      setTemplatesLoading(true);
      const data = await request<any>('/workspace-nexus/templates');
      setTemplates(data.templates || data || []);
    } catch (err: any) {
      alert('Failed to load templates: ' + err.message);
    } finally {
      setTemplatesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
    loadWorkspaces();
    loadContextFlows();
    loadTemplates();
  }, [loadOverview, loadWorkspaces, loadContextFlows, loadTemplates]);

  // Create workspace
  const handleCreateWorkspace = useCallback(async () => {
    if (!newWorkspace.name.trim()) {
      alert('Workspace name is required');
      return;
    }
    try {
      await request<any>('/workspace-nexus/workspaces', {
        method: 'POST',
        body: JSON.stringify(newWorkspace),
      });
      setNewWorkspace({ name: '', description: '', type: 'standard' });
      loadWorkspaces();
      loadOverview();
    } catch (err: any) {
      alert('Failed to create workspace: ' + err.message);
    }
  }, [newWorkspace, loadWorkspaces, loadOverview]);

  // Activate workspace
  const handleActivateWorkspace = useCallback(async (wsId: string) => {
    try {
      await request<any>(`/workspace-nexus/workspaces/${wsId}/activate`, { method: 'POST' });
      loadWorkspaces();
    } catch (err: any) {
      alert('Failed to activate workspace: ' + err.message);
    }
  }, [loadWorkspaces]);

  // Archive workspace
  const handleArchiveWorkspace = useCallback(async (wsId: string) => {
    if (!confirm('Archive this workspace?')) return;
    try {
      await request<any>(`/workspace-nexus/workspaces/${wsId}/archive`, { method: 'POST' });
      loadWorkspaces();
    } catch (err: any) {
      alert('Failed to archive workspace: ' + err.message);
    }
  }, [loadWorkspaces]);

  // View analytics
  const handleViewAnalytics = useCallback(async () => {
    if (!analyticsWsId.trim()) {
      alert('Workspace ID is required');
      return;
    }
    try {
      const data = await request<any>(`/workspace-nexus/workspaces/${analyticsWsId}/analytics`);
      setAnalytics(data);
    } catch (err: any) {
      alert('Failed to load analytics: ' + err.message);
    }
  }, [analyticsWsId]);

  // Connect subsystem
  const handleConnect = useCallback(async () => {
    if (!subsystemId.trim()) {
      alert('Subsystem ID is required');
      return;
    }
    try {
      await request<any>('/workspace-nexus/connections', {
        method: 'POST',
        body: JSON.stringify({ subsystem, subsystem_id: subsystemId, action: 'connect' }),
      });
      setSubsystemId('');
      setConnections((prev: any[]) => [...prev, { subsystem, subsystem_id: subsystemId, status: 'connected' }]);
    } catch (err: any) {
      alert('Failed to connect: ' + err.message);
    }
  }, [subsystem, subsystemId]);

  // Disconnect subsystem
  const handleDisconnect = useCallback(async (subsys: string, id: string) => {
    try {
      await request<any>('/workspace-nexus/connections', {
        method: 'POST',
        body: JSON.stringify({ subsystem: subsys, subsystem_id: id, action: 'disconnect' }),
      });
      setConnections((prev: any[]) => prev.filter((c: any) => !(c.subsystem === subsys && c.subsystem_id === id)));
    } catch (err: any) {
      alert('Failed to disconnect: ' + err.message);
    }
  }, []);

  // Create context flow
  const handleCreateFlow = useCallback(async () => {
    if (!newFlow.name.trim() || !newFlow.source.trim() || !newFlow.target.trim()) {
      alert('Name, source, and target are required');
      return;
    }
    try {
      let rules: any = {};
      try { rules = JSON.parse(newFlow.rules); } catch {
        alert('Invalid JSON rules');
        return;
      }
      await request<any>('/workspace-nexus/context-flows', {
        method: 'POST',
        body: JSON.stringify({ name: newFlow.name, source: newFlow.source, target: newFlow.target, rules }),
      });
      setNewFlow({ name: '', source: '', target: '', rules: '{}' });
      loadContextFlows();
    } catch (err: any) {
      alert('Failed to create flow: ' + err.message);
    }
  }, [newFlow, loadContextFlows]);

  // Sync context
  const handleSyncContext = useCallback(async () => {
    if (!syncId.trim()) {
      alert('Flow ID is required');
      return;
    }
    try {
      await request<any>(`/workspace-nexus/context-flows/${syncId}/sync`, { method: 'POST' });
      alert('Context synced successfully');
    } catch (err: any) {
      alert('Failed to sync context: ' + err.message);
    }
  }, [syncId]);

  // Register template
  const handleRegisterTemplate = useCallback(async () => {
    if (!newTemplate.name.trim()) {
      alert('Template name is required');
      return;
    }
    try {
      let definition: any = {};
      try { definition = JSON.parse(newTemplate.definition); } catch {
        alert('Invalid JSON definition');
        return;
      }
      await request<any>('/workspace-nexus/templates', {
        method: 'POST',
        body: JSON.stringify({ name: newTemplate.name, description: newTemplate.description, definition }),
      });
      setNewTemplate({ name: '', description: '', definition: '{}' });
      loadTemplates();
    } catch (err: any) {
      alert('Failed to register template: ' + err.message);
    }
  }, [newTemplate, loadTemplates]);

  const subsystemOptions = ['memory', 'skills', 'tools', 'agents', 'knowledge'];

  if (loading) {
    return (
      <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
        <div className="panel-header">
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Workspace Nexus</h2>
          <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>Manage workspaces, connections, context flows, and templates</p>
        </div>
        <div className="panel-loading" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <span style={{ color: colors.textSecondary }}>Loading workspace nexus data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Workspace Nexus</h2>
        <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>
          Manage workspaces, connections, context flows, and templates
        </p>
        {error && (
          <div className="error-banner" style={{ padding: '10px 16px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', color: colors.red, marginTop: '8px', fontSize: '14px' }}>
            {error}
            <button onClick={() => { setError(null); loadOverview(); }} style={{ marginLeft: '8px', background: 'none', border: 'none', color: colors.red, cursor: 'pointer', fontWeight: 600 }}>Dismiss</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar" style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' as const }}>
          {[
            { label: 'Workspaces', value: stats.total_workspaces ?? stats.workspaces ?? '0', color: colors.accent },
            { label: 'Active', value: stats.active_workspaces ?? stats.active ?? '0', color: colors.green },
            { label: 'Connections', value: stats.total_connections ?? stats.connections ?? '0', color: colors.blue },
            { label: 'Flows', value: stats.total_flows ?? stats.flows ?? '0', color: colors.yellow },
            { label: 'Templates', value: stats.total_templates ?? stats.templates ?? '0', color: colors.accent },
          ].map((stat) => (
            <div key={stat.label} className="stat-item" style={{
              flex: '1 1 120px', minWidth: '120px', background: colors.card,
              border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '14px 18px',
              display: 'flex', alignItems: 'center', gap: '12px',
            }}>
              <div className="stat-content" style={{ display: 'flex', flexDirection: 'column' }}>
                <span className="stat-value" style={{ fontSize: '1.3rem', fontWeight: 800, color: colors.text }}>{stat.value}</span>
                <span className="stat-label" style={{ fontSize: '0.72rem', color: colors.textSecondary, fontWeight: 600 }}>{stat.label}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {(['Overview', 'Workspaces', 'Connections', 'Context', 'Templates'] as Tab[]).map((tab) => (
          <button key={tab} className={`forge-tab ${activeTab === tab ? 'active' : ''}`}
            style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'Overview' && stats && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Overview</h3>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Total Workspaces</span>
            <strong>{stats.total_workspaces ?? stats.workspaces ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Active Workspaces</span>
            <strong style={{ color: colors.green }}>{stats.active_workspaces ?? stats.active ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Connections</span>
            <strong>{stats.total_connections ?? stats.connections ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Context Flows</span>
            <strong>{stats.total_flows ?? stats.flows ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Templates</span>
            <strong>{stats.total_templates ?? stats.templates ?? 'N/A'}</strong>
          </div>

          {/* Summary section */}
          {summary && (
            <div style={{ marginTop: '20px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>System Summary</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
                {Object.entries(summary).map(([key, value]: [string, any]) => (
                  <div key={key} style={{
                    background: colors.bg, borderRadius: '8px', padding: '12px',
                    border: `1px solid ${colors.border}`, textAlign: 'center',
                  }}>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: colors.accent }}>
                      {typeof value === 'object' ? JSON.stringify(value).slice(0, 40) : String(value)}
                    </div>
                    <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '4px', textTransform: 'capitalize' }}>
                      {key.replace(/_/g, ' ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div style={{ marginTop: '16px' }}>
            <button onClick={loadOverview} style={btnSecondary}>Refresh</button>
          </div>
        </div>
      )}

      {/* Workspaces Tab */}
      {activeTab === 'Workspaces' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Workspaces</h3>

          {/* Create workspace */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Create New Workspace</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input type="text" value={newWorkspace.name}
                  onChange={(e) => setNewWorkspace({ ...newWorkspace, name: e.target.value })}
                  placeholder="Workspace name" style={{ ...inputStyle, flex: 1 }} />
                <select value={newWorkspace.type}
                  onChange={(e) => setNewWorkspace({ ...newWorkspace, type: e.target.value })}
                  style={{ ...inputStyle, width: '150px' }}>
                  <option value="standard">Standard</option>
                  <option value="isolated">Isolated</option>
                  <option value="shared">Shared</option>
                  <option value="sandbox">Sandbox</option>
                </select>
              </div>
              <input type="text" value={newWorkspace.description}
                onChange={(e) => setNewWorkspace({ ...newWorkspace, description: e.target.value })}
                placeholder="Description (optional)" style={inputStyle} />
              <button onClick={handleCreateWorkspace} style={btnPrimary}>Create Workspace</button>
            </div>
          </div>

          {/* Analytics viewer */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>View Analytics</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={analyticsWsId}
                onChange={(e) => setAnalyticsWsId(e.target.value)}
                placeholder="Workspace ID" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={handleViewAnalytics} style={btnPrimary}>View</button>
            </div>
            {analytics && (
              <pre style={{ fontSize: '12px', color: colors.text, whiteSpace: 'pre-wrap', margin: '8px 0 0', overflow: 'auto', maxHeight: '200px', background: colors.card, padding: '8px', borderRadius: '6px' }}>
                {JSON.stringify(analytics, null, 2)}
              </pre>
            )}
          </div>

          {/* Workspaces list */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>Workspaces ({workspaces.length})</span>
              <button onClick={loadWorkspaces} style={{ ...btnSecondary, fontSize: '12px', padding: '4px 12px' }}>Refresh</button>
            </div>
            {workspaces.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {workspacesLoading ? 'Loading workspaces...' : 'No workspaces yet'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {workspaces.map((ws: any, idx: number) => {
                  const wsId = ws.id || ws.workspace_id || `ws-${idx}`;
                  const isActive = ws.status === 'active';
                  return (
                    <div key={wsId} className="forge-skill-card"
                      style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                        border: `1px solid ${isActive ? colors.green : colors.border}`,
                      }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 600, fontSize: '14px' }}>{ws.name}</span>
                          {isActive && (
                            <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', background: colors.green + '22', color: colors.green, fontWeight: 600 }}>Active</span>
                          )}
                          <span style={{ fontSize: '11px', color: colors.textSecondary }}>{ws.type || 'standard'}</span>
                        </div>
                        {ws.description && (
                          <div style={{ fontSize: '12px', color: colors.textSecondary, marginTop: '2px' }}>{ws.description}</div>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        {!isActive && (
                          <button onClick={() => handleActivateWorkspace(wsId)}
                            style={{ ...btnSecondary, fontSize: '11px', padding: '4px 8px', color: colors.green, borderColor: colors.green }}>
                            Activate
                          </button>
                        )}
                        <button onClick={() => handleArchiveWorkspace(wsId)}
                          style={{ ...btnSecondary, fontSize: '11px', padding: '4px 8px', color: colors.yellow, borderColor: colors.yellow }}>
                          Archive
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Connections Tab */}
      {activeTab === 'Connections' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Subsystem Connections</h3>

          {/* Connect form */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Connect Subsystem</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <select value={subsystem}
                onChange={(e) => setSubsystem(e.target.value)}
                style={{ ...inputStyle, width: '150px' }}>
                {subsystemOptions.map((opt) => (
                  <option key={opt} value={opt}>{opt.charAt(0).toUpperCase() + opt.slice(1)}</option>
                ))}
              </select>
              <input type="text" value={subsystemId}
                onChange={(e) => setSubsystemId(e.target.value)}
                placeholder="Subsystem ID" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={handleConnect} style={btnPrimary}>Connect</button>
            </div>
          </div>

          {/* Connections list */}
          <div>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>
              Active Connections ({connections.length})
            </h4>
            {connections.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                No active connections. Connect a subsystem to get started.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {connections.map((conn: any, idx: number) => (
                  <div key={idx} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                    border: `1px solid ${colors.border}`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        width: '8px', height: '8px', borderRadius: '50%',
                        background: conn.status === 'connected' ? colors.green : colors.textSecondary,
                      }} />
                      <span style={{ fontWeight: 600, fontSize: '14px', textTransform: 'capitalize' }}>
                        {conn.subsystem}
                      </span>
                      <span style={{ fontSize: '12px', color: colors.textSecondary }}>
                        {conn.subsystem_id}
                      </span>
                    </div>
                    <button onClick={() => handleDisconnect(conn.subsystem, conn.subsystem_id)}
                      style={{ ...btnSecondary, fontSize: '12px', padding: '4px 12px', color: colors.red, borderColor: colors.red }}>
                      Disconnect
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Context Tab */}
      {activeTab === 'Context' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Context Flows</h3>

          {/* Create flow */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Create Context Flow</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <input type="text" value={newFlow.name}
                onChange={(e) => setNewFlow({ ...newFlow, name: e.target.value })}
                placeholder="Flow name" style={inputStyle} />
              <div style={{ display: 'flex', gap: '8px' }}>
                <input type="text" value={newFlow.source}
                  onChange={(e) => setNewFlow({ ...newFlow, source: e.target.value })}
                  placeholder="Source" style={{ ...inputStyle, flex: 1 }} />
                <input type="text" value={newFlow.target}
                  onChange={(e) => setNewFlow({ ...newFlow, target: e.target.value })}
                  placeholder="Target" style={{ ...inputStyle, flex: 1 }} />
              </div>
              <textarea value={newFlow.rules}
                onChange={(e) => setNewFlow({ ...newFlow, rules: e.target.value })}
                placeholder='Rules (JSON)'
                rows={3}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }} />
              <button onClick={handleCreateFlow} style={btnPrimary}>Create Flow</button>
            </div>
          </div>

          {/* Sync context */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>Sync Context</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={syncId}
                onChange={(e) => setSyncId(e.target.value)}
                placeholder="Flow ID" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={handleSyncContext} style={btnPrimary}>Sync</button>
            </div>
          </div>

          {/* Flows list */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>Flows ({contextFlows.length})</span>
              <button onClick={loadContextFlows} style={{ ...btnSecondary, fontSize: '12px', padding: '4px 12px' }}>Refresh</button>
            </div>
            {contextFlows.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {contextLoading ? 'Loading flows...' : 'No context flows configured yet'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {contextFlows.map((flow: any, idx: number) => (
                  <div key={flow.id || flow.flow_id || idx} className="forge-skill-card"
                    style={{
                      padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                      border: `1px solid ${colors.border}`,
                    }}>
                    <div style={{ fontWeight: 600, fontSize: '14px' }}>{flow.name}</div>
                    <div style={{ fontSize: '12px', color: colors.textSecondary, marginTop: '4px' }}>
                      {flow.source} → {flow.target}
                    </div>
                    {flow.rules && (
                      <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '4px' }}>
                        Rules: {typeof flow.rules === 'string' ? flow.rules : JSON.stringify(flow.rules)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === 'Templates' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Workspace Templates</h3>

          {/* Register template */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Register New Template</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <input type="text" value={newTemplate.name}
                onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                placeholder="Template name" style={inputStyle} />
              <input type="text" value={newTemplate.description}
                onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
                placeholder="Description" style={inputStyle} />
              <textarea value={newTemplate.definition}
                onChange={(e) => setNewTemplate({ ...newTemplate, definition: e.target.value })}
                placeholder='Definition (JSON)'
                rows={4}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }} />
              <button onClick={handleRegisterTemplate} style={btnPrimary}>Register Template</button>
            </div>
          </div>

          {/* Templates list */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>Templates ({templates.length})</span>
              <button onClick={loadTemplates} style={{ ...btnSecondary, fontSize: '12px', padding: '4px 12px' }}>Refresh</button>
            </div>
            {templates.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {templatesLoading ? 'Loading templates...' : 'No workspace templates registered yet'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {templates.map((tmpl: any, idx: number) => (
                  <div key={tmpl.id || tmpl.template_id || idx} className="forge-skill-card"
                    style={{
                      padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                      border: `1px solid ${colors.border}`,
                    }}>
                    <div style={{ fontWeight: 600, fontSize: '14px' }}>{tmpl.name}</div>
                    {tmpl.description && (
                      <div style={{ fontSize: '12px', color: colors.textSecondary, marginTop: '4px' }}>{tmpl.description}</div>
                    )}
                    {tmpl.definition && (
                      <pre style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '4px', whiteSpace: 'pre-wrap', overflow: 'auto', maxHeight: '100px', background: colors.card, padding: '8px', borderRadius: '6px' }}>
                        {typeof tmpl.definition === 'string' ? tmpl.definition : JSON.stringify(tmpl.definition, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};