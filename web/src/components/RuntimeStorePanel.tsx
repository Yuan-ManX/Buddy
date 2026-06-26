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

interface RuntimeStoreStats {
  total_agents: number;
  total_snapshots: number;
  total_size_bytes: number;
  compression_ratio: number;
  total_checkpoints: number;
  total_diffs: number;
}

interface StoreAgent {
  id: string;
  name: string;
  state: string;
  snapshot_count: number;
  last_snapshot_at: string;
  size_bytes: number;
}

interface Snapshot {
  id: string;
  agent_id: string;
  version: number;
  state: string;
  size_bytes: number;
  compressed: boolean;
  created_at: string;
  summary: string;
}

interface Checkpoint {
  id: string;
  agent_id: string;
  snapshot_id: string;
  label: string;
  created_at: string;
  data_size_bytes: number;
}

interface Diff {
  id: string;
  agent_id: string;
  from_snapshot_id: string;
  to_snapshot_id: string;
  changes: number;
  additions: number;
  deletions: number;
  created_at: string;
}

type Tab = 'overview' | 'agents' | 'snapshots' | 'checkpoints' | 'diffs';

export const RuntimeStorePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview
  const [stats, setStats] = useState<RuntimeStoreStats | null>(null);

  // Agents
  const [agents, setAgents] = useState<StoreAgent[]>([]);

  // Snapshots
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [createSnapshotLabel, setCreateSnapshotLabel] = useState('');

  // Checkpoints
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [checkpointAgentId, setCheckpointAgentId] = useState('');
  const [checkpointLabel, setCheckpointLabel] = useState('');

  // Diffs
  const [diffs, setDiffs] = useState<Diff[]>([]);
  const [diffAgentId, setDiffAgentId] = useState('');
  const [diffForm, setDiffForm] = useState({ from_snapshot_id: '', to_snapshot_id: '' });
  const [diffResult, setDiffResult] = useState<Diff | null>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<RuntimeStoreStats>('/runtime-store/stats');
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load runtime store stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAgents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ agents: StoreAgent[] }>('/runtime-store/agents');
      setAgents(data.agents || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSnapshots = useCallback(async (agentId: string) => {
    if (!agentId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ snapshots: Snapshot[] }>(`/runtime-store/agents/${agentId}/snapshots`);
      setSnapshots(data.snapshots || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load snapshots');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCheckpoints = useCallback(async (agentId: string) => {
    if (!agentId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ checkpoints: Checkpoint[] }>(`/runtime-store/agents/${agentId}/checkpoints`);
      setCheckpoints(data.checkpoints || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load checkpoints');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDiffs = useCallback(async (agentId: string) => {
    if (!agentId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ diffs: Diff[] }>(`/runtime-store/agents/${agentId}/diffs`);
      setDiffs(data.diffs || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load diffs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadAgents();
  }, [loadStats, loadAgents]);

  const handleCreateSnapshot = async () => {
    if (!selectedAgentId) return;
    try {
      await request(`/runtime-store/agents/${selectedAgentId}/snapshots`, {
        method: 'POST',
        body: JSON.stringify({ label: createSnapshotLabel || undefined }),
      });
      setCreateSnapshotLabel('');
      loadSnapshots(selectedAgentId);
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to create snapshot');
    }
  };

  const handleCreateCheckpoint = async () => {
    if (!checkpointAgentId || !checkpointLabel.trim()) return;
    try {
      await request(`/runtime-store/agents/${checkpointAgentId}/checkpoints`, {
        method: 'POST',
        body: JSON.stringify({ label: checkpointLabel }),
      });
      setCheckpointLabel('');
      loadCheckpoints(checkpointAgentId);
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to create checkpoint');
    }
  };

  const handleCreateDiff = async () => {
    if (!diffAgentId || !diffForm.from_snapshot_id || !diffForm.to_snapshot_id) return;
    try {
      const data = await request<Diff>(`/runtime-store/agents/${diffAgentId}/diffs`, {
        method: 'POST',
        body: JSON.stringify(diffForm),
      });
      setDiffResult(data);
      loadDiffs(diffAgentId);
    } catch (e: any) {
      setError(e.message || 'Failed to create diff');
    }
  };

  const handleRestoreSnapshot = async (agentId: string, snapshotId: string) => {
    if (!confirm('Restore agent to this snapshot?')) return;
    try {
      await request(`/runtime-store/agents/${agentId}/snapshots/${snapshotId}/restore`, {
        method: 'POST',
      });
      loadSnapshots(agentId);
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to restore snapshot');
    }
  };

  const handleDeleteSnapshot = async (agentId: string, snapshotId: string) => {
    if (!confirm('Delete this snapshot?')) return;
    try {
      await request(`/runtime-store/agents/${agentId}/snapshots/${snapshotId}`, {
        method: 'DELETE',
      });
      loadSnapshots(agentId);
      loadStats();
    } catch (e: any) {
      setError(e.message || 'Failed to delete snapshot');
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const stateColor = (state: string) => {
    switch (state) {
      case 'running': return '#3b82f6';
      case 'paused': return '#f59e0b';
      case 'stopped': return '#6b7280';
      case 'error': return '#ef4444';
      default: return '#9ca3af';
    }
  };

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '8px 16px',
    background: activeTab === tab ? '#3b82f6' : '#f3f4f6',
    color: activeTab === tab ? '#fff' : '#374151',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: activeTab === tab ? 600 : 400,
    fontSize: 13,
  });

  const statCardStyle: React.CSSProperties = {
    flex: 1,
    background: '#f9fafb',
    borderRadius: 12,
    padding: 16,
    textAlign: 'center',
    border: '1px solid #e5e7eb',
  };

  if (loading && !stats && agents.length === 0) {
    return <div style={{ padding: 24, color: '#6b7280' }}>Loading runtime store data...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Agent Runtime Store</h2>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0', fontSize: 13 }}>State snapshot, checkpoint, and diff management</p>
        </div>
        <button
          style={tabStyle('overview')}
          onClick={() => { loadStats(); loadAgents(); }}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: '#fef2f2', borderRadius: 8, color: '#dc2626', marginBottom: 16, fontSize: 13 }}>
          {error}
          <button style={{ marginLeft: 12, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {(['overview', 'agents', 'snapshots', 'checkpoints', 'diffs'] as Tab[]).map(tab => (
          <button key={tab} style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && stats && (
        <div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_agents}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Agents</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.total_snapshots}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Snapshots</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#059669' }}>{formatBytes(stats.total_size_bytes)}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Size</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ea580c' }}>{stats.compression_ratio.toFixed(1)}x</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Compression Ratio</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Storage Summary</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ color: '#6b7280' }}>Checkpoints</span>
                  <span style={{ fontWeight: 600 }}>{stats.total_checkpoints}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ color: '#6b7280' }}>Diffs Tracked</span>
                  <span style={{ fontWeight: 600 }}>{stats.total_diffs}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ color: '#6b7280' }}>Avg Snapshot Size</span>
                  <span style={{ fontWeight: 600 }}>
                    {stats.total_snapshots > 0 ? formatBytes(stats.total_size_bytes / stats.total_snapshots) : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
            <div style={{ flex: 2, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Registered Agents</h3>
              {agents.length === 0 ? (
                <div style={{ color: '#9ca3af', fontSize: 13 }}>No agents registered in the runtime store.</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Agent</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>State</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Snapshots</th>
                      <th style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 500 }}>Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.slice(0, 10).map(agent => (
                      <tr key={agent.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '6px 8px', fontWeight: 500 }}>{agent.name}</td>
                        <td style={{ padding: '6px 8px' }}>
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: 12,
                            background: stateColor(agent.state),
                            color: '#fff',
                            fontSize: 11,
                            fontWeight: 600,
                          }}>
                            {agent.state}
                          </span>
                        </td>
                        <td style={{ padding: '6px 8px' }}>{agent.snapshot_count}</td>
                        <td style={{ padding: '6px 8px', fontFamily: 'monospace', fontSize: 12 }}>{formatBytes(agent.size_bytes)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Agents Tab */}
      {activeTab === 'agents' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>All Store Agents</h3>
            <button
              onClick={loadAgents}
              style={{ padding: '6px 12px', background: '#f3f4f6', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
            >
              Refresh
            </button>
          </div>
          {agents.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No agents found in the runtime store.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>ID</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Name</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>State</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Snapshots</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Last Snapshot</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Size</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {agents.map(agent => (
                  <tr key={agent.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>{agent.id}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{agent.name}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: stateColor(agent.state),
                        color: '#fff',
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {agent.state}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>{agent.snapshot_count}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>
                      {agent.last_snapshot_at ? new Date(agent.last_snapshot_at).toLocaleString() : 'Never'}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{formatBytes(agent.size_bytes)}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          onClick={() => {
                            setSelectedAgentId(agent.id);
                            loadSnapshots(agent.id);
                            setActiveTab('snapshots');
                          }}
                          style={{ padding: '4px 8px', background: '#eff6ff', color: '#2563eb', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Snapshots
                        </button>
                        <button
                          onClick={() => {
                            setCheckpointAgentId(agent.id);
                            loadCheckpoints(agent.id);
                            setActiveTab('checkpoints');
                          }}
                          style={{ padding: '4px 8px', background: '#f0fdf4', color: '#059669', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Checkpoints
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Snapshots Tab */}
      {activeTab === 'snapshots' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Snapshots {selectedAgentId ? `for ${selectedAgentId}` : ''}
            </h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={selectedAgentId}
                onChange={e => {
                  setSelectedAgentId(e.target.value);
                  if (e.target.value) loadSnapshots(e.target.value);
                }}
                style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              >
                <option value="">Select Agent...</option>
                {agents.map(a => <option key={a.id} value={a.id}>{a.name} ({a.id})</option>)}
              </select>
            </div>
          </div>

          {selectedAgentId && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, padding: 12, background: '#f9fafb', borderRadius: 8, border: '1px solid #e5e7eb' }}>
              <input
                value={createSnapshotLabel}
                onChange={e => setCreateSnapshotLabel(e.target.value)}
                placeholder="Snapshot label (optional)..."
                style={{ flex: 1, padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              />
              <button
                onClick={handleCreateSnapshot}
                style={{ padding: '6px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
              >
                Create Snapshot
              </button>
            </div>
          )}

          {!selectedAgentId ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Select an agent to view its snapshots.</div>
          ) : snapshots.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No snapshots found for this agent. Create one above.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Version</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>State</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Size</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Compressed</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Summary</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Created</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.map(snap => (
                  <tr key={snap.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>v{snap.version}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: stateColor(snap.state),
                        color: '#fff',
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {snap.state}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{formatBytes(snap.size_bytes)}</td>
                    <td style={{ padding: '10px 12px' }}>
                      {snap.compressed ? <span style={{ color: '#059669' }}>Yes</span> : <span style={{ color: '#9ca3af' }}>No</span>}
                    </td>
                    <td style={{ padding: '10px 12px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#6b7280' }}>
                      {snap.summary || '-'}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(snap.created_at).toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          onClick={() => handleRestoreSnapshot(selectedAgentId, snap.id)}
                          style={{ padding: '4px 8px', background: '#fef3c7', color: '#d97706', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Restore
                        </button>
                        <button
                          onClick={() => handleDeleteSnapshot(selectedAgentId, snap.id)}
                          style={{ padding: '4px 8px', background: '#fef2f2', color: '#dc2626', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Checkpoints Tab */}
      {activeTab === 'checkpoints' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Checkpoints {checkpointAgentId ? `for ${checkpointAgentId}` : ''}
            </h3>
            <select
              value={checkpointAgentId}
              onChange={e => {
                setCheckpointAgentId(e.target.value);
                if (e.target.value) loadCheckpoints(e.target.value);
              }}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">Select Agent...</option>
              {agents.map(a => <option key={a.id} value={a.id}>{a.name} ({a.id})</option>)}
            </select>
          </div>

          {checkpointAgentId && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, padding: 12, background: '#f9fafb', borderRadius: 8, border: '1px solid #e5e7eb' }}>
              <input
                value={checkpointLabel}
                onChange={e => setCheckpointLabel(e.target.value)}
                placeholder="Checkpoint label..."
                style={{ flex: 1, padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              />
              <button
                onClick={handleCreateCheckpoint}
                disabled={!checkpointLabel.trim()}
                style={{
                  padding: '6px 16px',
                  background: checkpointLabel.trim() ? '#059669' : '#d1d5db',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: checkpointLabel.trim() ? 'pointer' : 'default',
                  fontSize: 13,
                  fontWeight: 500,
                }}
              >
                Create Checkpoint
              </button>
            </div>
          )}

          {!checkpointAgentId ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Select an agent to view its checkpoints.</div>
          ) : checkpoints.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No checkpoints found for this agent.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Label</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Snapshot ID</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Data Size</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {checkpoints.map(cp => (
                  <tr key={cp.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{cp.label}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>{cp.snapshot_id}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{formatBytes(cp.data_size_bytes)}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(cp.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Diffs Tab */}
      {activeTab === 'diffs' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Diffs {diffAgentId ? `for ${diffAgentId}` : ''}
            </h3>
            <select
              value={diffAgentId}
              onChange={e => {
                setDiffAgentId(e.target.value);
                if (e.target.value) loadDiffs(e.target.value);
              }}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">Select Agent...</option>
              {agents.map(a => <option key={a.id} value={a.id}>{a.name} ({a.id})</option>)}
            </select>
          </div>

          {diffAgentId && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, padding: 12, background: '#f9fafb', borderRadius: 8, border: '1px solid #e5e7eb', flexWrap: 'wrap' }}>
              <input
                value={diffForm.from_snapshot_id}
                onChange={e => setDiffForm(prev => ({ ...prev, from_snapshot_id: e.target.value }))}
                placeholder="From Snapshot ID..."
                style={{ flex: 1, minWidth: 180, padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              />
              <input
                value={diffForm.to_snapshot_id}
                onChange={e => setDiffForm(prev => ({ ...prev, to_snapshot_id: e.target.value }))}
                placeholder="To Snapshot ID..."
                style={{ flex: 1, minWidth: 180, padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              />
              <button
                onClick={handleCreateDiff}
                disabled={!diffForm.from_snapshot_id || !diffForm.to_snapshot_id}
                style={{
                  padding: '6px 16px',
                  background: (!diffForm.from_snapshot_id || !diffForm.to_snapshot_id) ? '#d1d5db' : '#7c3aed',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: (!diffForm.from_snapshot_id || !diffForm.to_snapshot_id) ? 'default' : 'pointer',
                  fontSize: 13,
                  fontWeight: 500,
                }}
              >
                Compute Diff
              </button>
            </div>
          )}

          {diffResult && (
            <div style={{ marginBottom: 16, padding: 16, background: '#f5f3ff', borderRadius: 12, border: '1px solid #ddd6fe' }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 8px 0', color: '#7c3aed' }}>Diff Result</h4>
              <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                <div><span style={{ color: '#6b7280' }}>Changes:</span> <strong>{diffResult.changes}</strong></div>
                <div><span style={{ color: '#6b7280' }}>Additions:</span> <strong style={{ color: '#059669' }}>+{diffResult.additions}</strong></div>
                <div><span style={{ color: '#6b7280' }}>Deletions:</span> <strong style={{ color: '#dc2626' }}>-{diffResult.deletions}</strong></div>
              </div>
            </div>
          )}

          {!diffAgentId ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>Select an agent to view its diffs.</div>
          ) : diffs.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No diffs found for this agent.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
              <thead>
                <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>From</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>To</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Changes</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Additions</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Deletions</th>
                  <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Created</th>
                </tr>
              </thead>
              <tbody>
                {diffs.map(diff => (
                  <tr key={diff.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>{diff.from_snapshot_id.substring(0, 12)}...</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>{diff.to_snapshot_id.substring(0, 12)}...</td>
                    <td style={{ padding: '10px 12px' }}>{diff.changes}</td>
                    <td style={{ padding: '10px 12px', color: '#059669' }}>+{diff.additions}</td>
                    <td style={{ padding: '10px 12px', color: '#dc2626' }}>-{diff.deletions}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(diff.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
};