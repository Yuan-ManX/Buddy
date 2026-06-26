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

type Tab = 'Overview' | 'Groups' | 'Batches' | 'Lifecycle' | 'Templates';

export const SessionCommanderPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('Overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview tab state
  const [stats, setStats] = useState<any>(null);

  // Groups tab state
  const [groups, setGroups] = useState<any[]>([]);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDesc, setNewGroupDesc] = useState('');

  // Batches tab state
  const [batchSessionIds, setBatchSessionIds] = useState('');
  const [batchResult, setBatchResult] = useState<any>(null);
  const [batchLoading, setBatchLoading] = useState(false);

  // Lifecycle tab state
  const [lifecycleSessionId, setLifecycleSessionId] = useState('');
  const [lifecycleResult, setLifecycleResult] = useState<any>(null);
  const [lifecycleLoading, setLifecycleLoading] = useState(false);
  const [snapshotDesc, setSnapshotDesc] = useState('');
  const [branchName, setBranchName] = useState('');
  const [mergeSourceId, setMergeSourceId] = useState('');

  // Templates tab state
  const [templates, setTemplates] = useState<any[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [newTemplate, setNewTemplate] = useState({ name: '', description: '', config: '{}' });

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

  // Load overview stats
  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<any>('/session-commander/stats');
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load groups
  const loadGroups = useCallback(async () => {
    try {
      setGroupsLoading(true);
      const data = await request<any>('/session-commander/groups');
      setGroups(data.groups || data || []);
    } catch (err: any) {
      alert('Failed to load groups: ' + err.message);
    } finally {
      setGroupsLoading(false);
    }
  }, []);

  // Load templates
  const loadTemplates = useCallback(async () => {
    try {
      setTemplatesLoading(true);
      const data = await request<any>('/session-commander/templates');
      setTemplates(data.templates || data || []);
    } catch (err: any) {
      alert('Failed to load templates: ' + err.message);
    } finally {
      setTemplatesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadGroups();
    loadTemplates();
  }, [loadStats, loadGroups, loadTemplates]);

  // Create group
  const handleCreateGroup = useCallback(async () => {
    if (!newGroupName.trim()) {
      alert('Group name is required');
      return;
    }
    try {
      await request<any>('/session-commander/groups', {
        method: 'POST',
        body: JSON.stringify({ name: newGroupName, description: newGroupDesc }),
      });
      setNewGroupName('');
      setNewGroupDesc('');
      loadGroups();
    } catch (err: any) {
      alert('Failed to create group: ' + err.message);
    }
  }, [newGroupName, newGroupDesc, loadGroups]);

  // Delete group
  const handleDeleteGroup = useCallback(async (groupId: string) => {
    if (!confirm('Delete this group?')) return;
    try {
      await request<any>(`/session-commander/groups/${groupId}`, { method: 'DELETE' });
      loadGroups();
    } catch (err: any) {
      alert('Failed to delete group: ' + err.message);
    }
  }, [loadGroups]);

  // Batch operation
  const handleBatchOperation = useCallback(async (operation: string) => {
    const ids = batchSessionIds.split(',').map((s) => s.trim()).filter(Boolean);
    if (ids.length === 0) {
      alert('Please enter at least one session ID');
      return;
    }
    try {
      setBatchLoading(true);
      const data = await request<any>('/session-commander/batch', {
        method: 'POST',
        body: JSON.stringify({ operation, session_ids: ids }),
      });
      setBatchResult(data);
    } catch (err: any) {
      alert(`Batch ${operation} failed: ` + err.message);
    } finally {
      setBatchLoading(false);
    }
  }, [batchSessionIds]);

  // Lifecycle operations
  const handleLifecycle = useCallback(async (operation: string) => {
    if (!lifecycleSessionId.trim()) {
      alert('Session ID is required');
      return;
    }
    try {
      setLifecycleLoading(true);
      let body: any = { session_id: lifecycleSessionId };
      if (operation === 'snapshot') body.description = snapshotDesc;
      if (operation === 'branch') body.branch_name = branchName;
      if (operation === 'restore') body.snapshot_id = snapshotDesc;
      if (operation === 'merge') body.source_session_id = mergeSourceId;

      const data = await request<any>(`/session-commander/lifecycle/${operation}`, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      setLifecycleResult({ operation, data });
      if (operation === 'snapshot') setSnapshotDesc('');
      if (operation === 'branch') setBranchName('');
      if (operation === 'merge') setMergeSourceId('');
    } catch (err: any) {
      alert(`Lifecycle ${operation} failed: ` + err.message);
    } finally {
      setLifecycleLoading(false);
    }
  }, [lifecycleSessionId, snapshotDesc, branchName, mergeSourceId]);

  // Create template
  const handleCreateTemplate = useCallback(async () => {
    if (!newTemplate.name.trim()) {
      alert('Template name is required');
      return;
    }
    try {
      let config: any = {};
      try { config = JSON.parse(newTemplate.config); } catch {
        alert('Invalid JSON config');
        return;
      }
      await request<any>('/session-commander/templates', {
        method: 'POST',
        body: JSON.stringify({ name: newTemplate.name, description: newTemplate.description, config }),
      });
      setNewTemplate({ name: '', description: '', config: '{}' });
      loadTemplates();
    } catch (err: any) {
      alert('Failed to create template: ' + err.message);
    }
  }, [newTemplate, loadTemplates]);

  if (loading) {
    return (
      <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
        <div className="panel-header">
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Session Commander</h2>
          <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>Manage session groups, batches, lifecycles, and templates</p>
        </div>
        <div className="panel-loading" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <span style={{ color: colors.textSecondary }}>Loading session commander data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Session Commander</h2>
        <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>
          Manage session groups, batches, lifecycles, and templates
        </p>
        {error && (
          <div className="error-banner" style={{ padding: '10px 16px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', color: colors.red, marginTop: '8px', fontSize: '14px' }}>
            {error}
            <button onClick={() => { setError(null); loadStats(); }} style={{ marginLeft: '8px', background: 'none', border: 'none', color: colors.red, cursor: 'pointer', fontWeight: 600 }}>Dismiss</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar" style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' as const }}>
          {[
            { label: 'Total Sessions', value: stats.total_sessions ?? stats.total ?? '0', color: colors.accent },
            { label: 'Active', value: stats.active_sessions ?? stats.active ?? '0', color: colors.green },
            { label: 'Groups', value: stats.total_groups ?? stats.groups ?? '0', color: colors.blue },
            { label: 'Templates', value: stats.total_templates ?? stats.templates ?? '0', color: colors.yellow },
            { label: 'Snapshots', value: stats.total_snapshots ?? stats.snapshots ?? '0', color: colors.accent },
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
        {(['Overview', 'Groups', 'Batches', 'Lifecycle', 'Templates'] as Tab[]).map((tab) => (
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
            <span style={{ color: colors.textSecondary }}>Total Sessions</span>
            <strong>{stats.total_sessions ?? stats.total ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Active Sessions</span>
            <strong style={{ color: colors.green }}>{stats.active_sessions ?? stats.active ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Groups</span>
            <strong>{stats.total_groups ?? stats.groups ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Templates</span>
            <strong>{stats.total_templates ?? stats.templates ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Snapshots</span>
            <strong>{stats.total_snapshots ?? stats.snapshots ?? 'N/A'}</strong>
          </div>
          <div style={{ marginTop: '16px' }}>
            <button onClick={loadStats} style={btnSecondary}>Refresh Stats</button>
          </div>
        </div>
      )}

      {/* Groups Tab */}
      {activeTab === 'Groups' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Session Groups</h3>

          {/* Create group */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Create New Group</h4>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input type="text" value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="Group name" style={{ ...inputStyle, flex: 1 }} />
            </div>
            <input type="text" value={newGroupDesc}
              onChange={(e) => setNewGroupDesc(e.target.value)}
              placeholder="Description (optional)" style={{ ...inputStyle, marginBottom: '8px' }} />
            <button onClick={handleCreateGroup} style={btnPrimary}>Create Group</button>
          </div>

          {/* Groups list */}
          <div>
            {groups.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {groupsLoading ? 'Loading groups...' : 'No session groups configured yet'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {groups.map((group: any, idx: number) => (
                  <div key={group.id || group.group_id || idx} className="forge-skill-card"
                    style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                      border: `1px solid ${colors.border}`,
                    }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>{group.name}</div>
                      {group.description && (
                        <div style={{ fontSize: '12px', color: colors.textSecondary, marginTop: '2px' }}>{group.description}</div>
                      )}
                      <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '2px' }}>
                        Sessions: {group.session_count ?? group.sessions ?? '0'}
                      </div>
                    </div>
                    <button onClick={() => handleDeleteGroup(group.id || group.group_id)}
                      style={{ ...btnSecondary, color: colors.red, borderColor: colors.red, fontSize: '12px', padding: '4px 12px' }}>
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Batches Tab */}
      {activeTab === 'Batches' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Batch Operations</h3>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Session IDs (comma-separated)</label>
            <textarea value={batchSessionIds}
              onChange={(e) => setBatchSessionIds(e.target.value)}
              placeholder="session-1, session-2, session-3"
              rows={2}
              style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }} />
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
            {[
              { op: 'summarize', label: 'Summarize', color: colors.blue },
              { op: 'archive', label: 'Archive', color: colors.yellow },
              { op: 'merge', label: 'Merge', color: colors.accent },
              { op: 'export', label: 'Export', color: colors.green },
              { op: 'delete', label: 'Delete', color: colors.red },
            ].map(({ op, label, color }) => (
              <button key={op} onClick={() => handleBatchOperation(op)} disabled={batchLoading}
                style={{
                  ...btnSecondary, borderColor: color, color,
                  opacity: batchLoading ? 0.5 : 1, cursor: batchLoading ? 'not-allowed' : 'pointer',
                }}>
                {batchLoading ? 'Processing...' : label}
              </button>
            ))}
          </div>
          {batchResult && (
            <div style={{ padding: '12px', background: colors.bg, borderRadius: '8px', border: `1px solid ${colors.border}` }}>
              <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600, color: colors.green }}>Batch Result</h4>
              <pre style={{ fontSize: '12px', color: colors.text, whiteSpace: 'pre-wrap', margin: 0, overflow: 'auto', maxHeight: '200px' }}>
                {JSON.stringify(batchResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Lifecycle Tab */}
      {activeTab === 'Lifecycle' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Session Lifecycle Management</h3>

          {/* Session ID input */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Session ID</label>
            <input type="text" value={lifecycleSessionId}
              onChange={(e) => setLifecycleSessionId(e.target.value)}
              placeholder="Enter session ID" style={inputStyle} />
          </div>

          {/* Pause/Resume */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
            {[
              { op: 'pause', label: 'Pause', color: colors.yellow },
              { op: 'resume', label: 'Resume', color: colors.green },
            ].map(({ op, label, color }) => (
              <button key={op} onClick={() => handleLifecycle(op)} disabled={lifecycleLoading}
                style={{
                  ...btnSecondary, borderColor: color, color,
                  opacity: lifecycleLoading ? 0.5 : 1, cursor: lifecycleLoading ? 'not-allowed' : 'pointer',
                }}>
                {label}
              </button>
            ))}
          </div>

          {/* Snapshot */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>Snapshot</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={snapshotDesc}
                onChange={(e) => setSnapshotDesc(e.target.value)}
                placeholder="Snapshot description" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={() => handleLifecycle('snapshot')} disabled={lifecycleLoading}
                style={{ ...btnPrimary, opacity: lifecycleLoading ? 0.5 : 1 }}>
                {lifecycleLoading ? '...' : 'Snapshot'}
              </button>
            </div>
          </div>

          {/* Restore */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>Restore</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={snapshotDesc}
                onChange={(e) => setSnapshotDesc(e.target.value)}
                placeholder="Snapshot ID" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={() => handleLifecycle('restore')} disabled={lifecycleLoading}
                style={{ ...btnPrimary, opacity: lifecycleLoading ? 0.5 : 1 }}>
                {lifecycleLoading ? '...' : 'Restore'}
              </button>
            </div>
          </div>

          {/* Branch */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>Branch</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
                placeholder="Branch name" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={() => handleLifecycle('branch')} disabled={lifecycleLoading}
                style={{ ...btnPrimary, opacity: lifecycleLoading ? 0.5 : 1 }}>
                {lifecycleLoading ? '...' : 'Branch'}
              </button>
            </div>
          </div>

          {/* Merge */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>Merge</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={mergeSourceId}
                onChange={(e) => setMergeSourceId(e.target.value)}
                placeholder="Source session ID to merge from" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={() => handleLifecycle('merge')} disabled={lifecycleLoading}
                style={{ ...btnPrimary, opacity: lifecycleLoading ? 0.5 : 1 }}>
                {lifecycleLoading ? '...' : 'Merge'}
              </button>
            </div>
          </div>

          {/* Lifecycle result */}
          {lifecycleResult && (
            <div style={{ padding: '12px', background: colors.bg, borderRadius: '8px', border: `1px solid ${colors.border}` }}>
              <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600, color: colors.green }}>
                {lifecycleResult.operation} Result
              </h4>
              <pre style={{ fontSize: '12px', color: colors.text, whiteSpace: 'pre-wrap', margin: 0, overflow: 'auto', maxHeight: '200px' }}>
                {JSON.stringify(lifecycleResult.data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === 'Templates' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Session Templates</h3>

          {/* Create template */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Create New Template</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <input type="text" value={newTemplate.name}
                onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                placeholder="Template name" style={inputStyle} />
              <input type="text" value={newTemplate.description}
                onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
                placeholder="Description" style={inputStyle} />
              <textarea value={newTemplate.config}
                onChange={(e) => setNewTemplate({ ...newTemplate, config: e.target.value })}
                placeholder='Config (JSON)'
                rows={4}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }} />
              <button onClick={handleCreateTemplate} style={btnPrimary}>Create Template</button>
            </div>
          </div>

          {/* Templates list */}
          <div>
            {templates.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {templatesLoading ? 'Loading templates...' : 'No session templates configured yet'}
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
                    {tmpl.config && (
                      <pre style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '4px', whiteSpace: 'pre-wrap', overflow: 'auto', maxHeight: '100px', background: colors.card, padding: '8px', borderRadius: '6px' }}>
                        {typeof tmpl.config === 'string' ? tmpl.config : JSON.stringify(tmpl.config, null, 2)}
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