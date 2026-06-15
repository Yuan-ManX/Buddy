import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { RuntimeBackendInfo, RuntimeInstanceInfo, RuntimeBackendStats, Agent } from '../types';

interface Props {
  agent?: Agent | null;
}

export const RuntimeBackendPanel: React.FC<Props> = ({ agent }) => {
  const [backends, setBackends] = useState<RuntimeBackendInfo[]>([]);
  const [instances, setInstances] = useState<RuntimeInstanceInfo[]>([]);
  const [stats, setStats] = useState<RuntimeBackendStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<RuntimeInstanceInfo | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [createForm, setCreateForm] = useState({
    agent_id: agent?.id || '', backend: 'buddy_native', workspace_dir: '', max_memory_mb: '512', max_cpu_cores: '2', timeout_seconds: '3600',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [b, i, s] = await Promise.all([
        api.runtimeBackend.backends(),
        api.runtimeBackend.instances(agent?.id || undefined),
        api.runtimeBackend.stats(),
      ]);
      setBackends(b.backends);
      setInstances(i.instances);
      setStats(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runtime backends');
    } finally {
      setLoading(false);
    }
  }, [agent?.id]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    try {
      await api.runtimeBackend.create({
        agent_id: createForm.agent_id,
        backend: createForm.backend,
        workspace_dir: createForm.workspace_dir,
        max_memory_mb: Number(createForm.max_memory_mb),
        max_cpu_cores: Number(createForm.max_cpu_cores),
        timeout_seconds: Number(createForm.timeout_seconds),
      });
      setShowCreate(false);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create instance');
    }
  };

  const handleTerminate = async (instanceId: string) => {
    try {
      await api.runtimeBackend.terminate(instanceId);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to terminate instance');
    }
  };

  const handleViewMetrics = async (instance: RuntimeInstanceInfo) => {
    setSelectedInstance(instance);
    try {
      const m = await api.runtimeBackend.metrics(instance.id);
      setMetrics(m);
    } catch {
      setMetrics({ error: 'Failed to load metrics' });
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      created: 'badge-gray',
      starting: 'badge-yellow',
      running: 'badge-green',
      idle: 'badge-blue',
      error: 'badge-red',
      terminated: 'badge-gray',
    };
    return colors[status] || 'badge-gray';
  };

  if (loading) return <div className="panel-loading">Loading runtime backends...</div>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Runtime Backend</h2>
        <div className="panel-header-actions">
          <button className="btn-primary" onClick={() => setShowCreate(true)}>Create Instance</button>
          <button className="btn-secondary" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_instances}</div>
            <div className="stat-label">Total Instances</div>
          </div>
          {Object.entries(stats.by_status).map(([status, count]) => (
            <div className="stat-card" key={status}>
              <div className="stat-value">{count}</div>
              <div className="stat-label">{status}</div>
            </div>
          ))}
        </div>
      )}

      <div className="panel-section">
        <h3>Available Backends</h3>
        <div className="card-grid">
          {backends.map((b) => (
            <div key={b.kind} className="card">
              <div className="card-header">
                <span className="item-name">{b.display_name}</span>
                <span className="badge badge-blue">{b.active_count} active</span>
              </div>
              <div className="card-body">
                <p>{b.capabilities.join(', ')}</p>
                <p>Total instances: {b.instance_count}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel-section">
        <h3>Runtime Instances</h3>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Instance</th>
                <th>Backend</th>
                <th>Status</th>
                <th>Agent</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {instances.map((inst) => (
                <tr key={inst.id} className={selectedInstance?.id === inst.id ? 'row-selected' : ''}>
                  <td>
                    <div className="item-name">{inst.id.slice(0, 12)}</div>
                  </td>
                  <td>{inst.backend}</td>
                  <td><span className={`badge ${getStatusBadge(inst.status)}`}>{inst.status}</span></td>
                  <td>{inst.agent_id ? inst.agent_id.slice(0, 8) : '-'}</td>
                  <td>{inst.created_at ? new Date(inst.created_at).toLocaleString() : '-'}</td>
                  <td>
                    <div className="btn-group">
                      <button className="btn-sm btn-blue" onClick={() => handleViewMetrics(inst)}>Metrics</button>
                      {inst.status !== 'terminated' && inst.status !== 'error' && (
                        <button className="btn-sm btn-red" onClick={() => handleTerminate(inst.id)}>Stop</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {instances.length === 0 && (
                <tr><td colSpan={6} className="empty-cell">No runtime instances. Create one to get started.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedInstance && metrics && (
        <div className="panel-section panel-section-highlight">
          <h3>Instance Metrics: {selectedInstance.id.slice(0, 12)}</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{selectedInstance.status}</div>
              <div className="stat-label">Status</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{selectedInstance.backend}</div>
              <div className="stat-label">Backend</div>
            </div>
          </div>
          <pre className="code-block">{JSON.stringify(metrics, null, 2)}</pre>
          <button className="btn-secondary" onClick={() => { setSelectedInstance(null); setMetrics(null); }}>Close</button>
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Runtime Instance</h2>
            <div className="form-group">
              <label>Backend</label>
              <select value={createForm.backend} onChange={e => setCreateForm({...createForm, backend: e.target.value})}>
                <option value="buddy_native">Buddy Native</option>
                <option value="langchain">LangChain</option>
                <option value="autogen">AutoGen</option>
                <option value="docker_container">Docker Container</option>
              </select>
            </div>
            <div className="form-group">
              <label>Agent ID</label>
              <input type="text" value={createForm.agent_id} onChange={e => setCreateForm({...createForm, agent_id: e.target.value})} placeholder="Agent ID" />
            </div>
            <div className="form-group">
              <label>Workspace Directory</label>
              <input type="text" value={createForm.workspace_dir} onChange={e => setCreateForm({...createForm, workspace_dir: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Max Memory (MB)</label>
              <input type="number" value={createForm.max_memory_mb} onChange={e => setCreateForm({...createForm, max_memory_mb: e.target.value})} min="64" />
            </div>
            <div className="form-group">
              <label>Max CPU Cores</label>
              <input type="number" value={createForm.max_cpu_cores} onChange={e => setCreateForm({...createForm, max_cpu_cores: e.target.value})} min="1" max="16" />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};