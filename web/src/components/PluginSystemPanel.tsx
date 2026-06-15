import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { PluginInfo, PluginStats } from '../types';

export const PluginSystemPanel: React.FC = () => {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [stats, setStats] = useState<PluginStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [showRegister, setShowRegister] = useState(false);
  const [registerForm, setRegisterForm] = useState({
    id: '', name: '', version: '1.0.0', description: '', author: '',
    homepage: '', permissions: '', capabilities: '', entry_point: '', tags: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [p, s] = await Promise.all([
        api.plugins.list(statusFilter || undefined),
        api.plugins.stats(),
      ]);
      setPlugins(p.plugins);
      setStats(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load plugins');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRegister = async () => {
    if (!registerForm.id || !registerForm.name) return;
    try {
      await api.plugins.register({
        id: registerForm.id,
        name: registerForm.name,
        version: registerForm.version,
        description: registerForm.description,
        author: registerForm.author,
        homepage: registerForm.homepage,
        permissions: registerForm.permissions ? registerForm.permissions.split(',').map(s => s.trim()) : [],
        capabilities: registerForm.capabilities ? registerForm.capabilities.split(',').map(s => s.trim()) : [],
        entry_point: registerForm.entry_point,
        tags: registerForm.tags ? registerForm.tags.split(',').map(s => s.trim()) : [],
      });
      setShowRegister(false);
      setRegisterForm({ id: '', name: '', version: '1.0.0', description: '', author: '', homepage: '', permissions: '', capabilities: '', entry_point: '', tags: '' });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register plugin');
    }
  };

  const handleAction = async (pluginId: string, action: 'install' | 'activate' | 'deactivate' | 'uninstall') => {
    try {
      switch (action) {
        case 'install': await api.plugins.install(pluginId); break;
        case 'activate': await api.plugins.activate(pluginId); break;
        case 'deactivate': await api.plugins.deactivate(pluginId); break;
        case 'uninstall': await api.plugins.uninstall(pluginId); break;
      }
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} plugin`);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      registered: 'badge-gray',
      installed: 'badge-blue',
      active: 'badge-green',
      error: 'badge-red',
    };
    return colors[status] || 'badge-gray';
  };

  if (loading) return <div className="panel-loading">Loading plugins...</div>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Plugin System</h2>
        <div className="panel-header-actions">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="form-select">
            <option value="">All Statuses</option>
            <option value="registered">Registered</option>
            <option value="installed">Installed</option>
            <option value="active">Active</option>
            <option value="error">Error</option>
          </select>
          <button className="btn-primary" onClick={() => setShowRegister(true)}>Register Plugin</button>
          <button className="btn-secondary" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_plugins}</div>
            <div className="stat-label">Total Plugins</div>
          </div>
          {Object.entries(stats.by_status).map(([status, count]) => (
            <div className="stat-card" key={status}>
              <div className="stat-value">{count}</div>
              <div className="stat-label">{status}</div>
            </div>
          ))}
        </div>
      )}

      {showRegister && (
        <div className="modal-overlay" onClick={() => setShowRegister(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Register Plugin</h2>
            <div className="form-group">
              <label>Plugin ID (required)</label>
              <input type="text" value={registerForm.id} onChange={e => setRegisterForm({...registerForm, id: e.target.value})} placeholder="my-plugin" />
            </div>
            <div className="form-group">
              <label>Name (required)</label>
              <input type="text" value={registerForm.name} onChange={e => setRegisterForm({...registerForm, name: e.target.value})} placeholder="My Plugin" />
            </div>
            <div className="form-group">
              <label>Version</label>
              <input type="text" value={registerForm.version} onChange={e => setRegisterForm({...registerForm, version: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea rows={2} value={registerForm.description} onChange={e => setRegisterForm({...registerForm, description: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Author</label>
              <input type="text" value={registerForm.author} onChange={e => setRegisterForm({...registerForm, author: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Tags (comma separated)</label>
              <input type="text" value={registerForm.tags} onChange={e => setRegisterForm({...registerForm, tags: e.target.value})} placeholder="ai, automation" />
            </div>
            <div className="form-group">
              <label>Permissions (comma separated)</label>
              <input type="text" value={registerForm.permissions} onChange={e => setRegisterForm({...registerForm, permissions: e.target.value})} placeholder="tools, memory" />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowRegister(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleRegister}>Register</button>
            </div>
          </div>
        </div>
      )}

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Plugin</th>
              <th>Version</th>
              <th>Author</th>
              <th>Status</th>
              <th>Tags</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {plugins.map((p) => (
              <tr key={p.id}>
                <td>
                  <div className="item-name">{p.name}</div>
                  <div className="item-desc">{p.description}</div>
                </td>
                <td>{p.version}</td>
                <td>{p.author}</td>
                <td><span className={`badge ${getStatusBadge(p.status)}`}>{p.status}</span></td>
                <td>{p.tags.slice(0, 3).map(t => <span key={t} className="badge badge-sm">{t}</span>)}</td>
                <td>
                  <div className="btn-group">
                    {p.status === 'registered' && (
                      <button className="btn-sm btn-blue" onClick={() => handleAction(p.id, 'install')}>Install</button>
                    )}
                    {p.status === 'installed' && (
                      <button className="btn-sm btn-green" onClick={() => handleAction(p.id, 'activate')}>Activate</button>
                    )}
                    {p.status === 'active' && (
                      <button className="btn-sm btn-yellow" onClick={() => handleAction(p.id, 'deactivate')}>Deactivate</button>
                    )}
                    {(p.status === 'installed' || p.status === 'active' || p.status === 'error') && (
                      <button className="btn-sm btn-red" onClick={() => handleAction(p.id, 'uninstall')}>Remove</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {plugins.length === 0 && (
              <tr><td colSpan={6} className="empty-cell">No plugins registered. Create one to get started.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};