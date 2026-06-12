import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import type { Workspace, WorkspaceStatsOverview } from '../types';

export const WorkspacePanel: React.FC = () => {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [stats, setStats] = useState<WorkspaceStatsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [newWorkspace, setNewWorkspace] = useState({ name: '', description: '' });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [wsList, wsStats] = await Promise.all([
        api.workspaces.list(),
        api.workspaces.stats(),
      ]);
      setWorkspaces(wsList);
      setStats(wsStats);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load workspaces');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newWorkspace.name.trim()) return;
    try {
      await api.workspaces.create({
        name: newWorkspace.name.trim(),
        description: newWorkspace.description.trim(),
      });
      setShowCreate(false);
      setNewWorkspace({ name: '', description: '' });
      toast.success('Workspace created');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to create workspace');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.workspaces.delete(id);
      setDeleteConfirm(null);
      toast.success('Workspace deleted');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to delete workspace');
    }
  };

  const handleSwitch = async (id: string) => {
    try {
      await api.workspaces.switch(id);
      toast.success('Active workspace switched');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to switch workspace');
    }
  };

  const handleExport = async (id: string) => {
    try {
      const data = await api.workspaces.export(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workspace-${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Workspace exported');
    } catch (e: any) {
      toast.error(e.message || 'Failed to export workspace');
    }
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const imported = JSON.parse(text);
      if (imported.workspace) {
        await api.workspaces.create({
          name: imported.workspace.name || 'Imported Workspace',
          description: imported.workspace.description || '',
        });
        toast.success('Workspace imported');
        loadData();
      } else {
        toast.error('Invalid workspace export file');
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to import workspace');
    }
    e.target.value = '';
  };

  const formatTime = (iso: string) => iso ? new Date(iso).toLocaleString() : 'N/A';

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Workspaces</h2>
          <p className="panel-subtitle">Manage isolated workspaces for agents</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading workspaces...</span></div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Workspaces</h2>
        <p className="panel-subtitle">Manage isolated workspaces for agents</p>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-icon">📁</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_workspaces}</span>
              <span className="stat-label">Total Workspaces</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">🟢</span>
            <div className="stat-content">
              <span className="stat-value">{stats.active_workspaces}</span>
              <span className="stat-label">Active</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">📄</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_files}</span>
              <span className="stat-label">Total Files</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">🧠</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_memories}</span>
              <span className="stat-label">Total Memories</span>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="action-bar">
        <button className="btn-primary-sm" onClick={() => setShowCreate(true)}>+ New Workspace</button>
        <button className="btn-secondary-sm" onClick={handleImportClick}>📥 Import</button>
        <button className="btn-secondary-sm" onClick={loadData}>🔄 Refresh</button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          style={{ display: 'none' }}
          onChange={handleImportFile}
        />
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create Workspace</h3>
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={newWorkspace.name}
                onChange={e => setNewWorkspace({ ...newWorkspace, name: e.target.value })}
                placeholder="Workspace name"
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={2}
                value={newWorkspace.description}
                onChange={e => setNewWorkspace({ ...newWorkspace, description: e.target.value })}
                placeholder="Optional description"
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Delete Workspace</h3>
            <p style={{ color: 'var(--text-secondary, #6b7280)', marginBottom: 20, fontSize: '0.9rem' }}>
              Are you sure you want to delete this workspace? This action cannot be undone.
            </p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setDeleteConfirm(null)}>Cancel</button>
              <button className="btn-danger" onClick={() => handleDelete(deleteConfirm)}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Workspace List */}
      <div className="workspace-list">
        {workspaces.length === 0 ? (
          <div className="panel-empty">
            <p>No workspaces yet</p>
            <p>Create your first workspace to get started</p>
          </div>
        ) : (
          workspaces.map(ws => (
            <div key={ws.id} className={`workspace-card ${ws.is_active ? 'active' : ''}`}>
              <div className="workspace-card-header">
                <div className="workspace-title-row">
                  {ws.is_active && <span className="active-dot" title="Active workspace" />}
                  <h4 className="workspace-name">{ws.name}</h4>
                  {ws.is_active && <span className="active-badge">Active</span>}
                </div>
                <div className="workspace-card-actions">
                  <button
                    className="btn-mini"
                    onClick={() => handleExport(ws.id)}
                    title="Export workspace"
                  >
                    📤 Export
                  </button>
                  {!ws.is_active && (
                    <button
                      className="btn-mini"
                      onClick={() => handleSwitch(ws.id)}
                      title="Switch to this workspace"
                    >
                      🔄 Activate
                    </button>
                  )}
                  <button
                    className="btn-mini danger"
                    onClick={() => setDeleteConfirm(ws.id)}
                    title="Delete workspace"
                  >
                    × Delete
                  </button>
                </div>
              </div>
              {ws.description && (
                <p className="workspace-description">{ws.description}</p>
              )}
              <div className="workspace-meta-row">
                <div className="workspace-meta">
                  <span className="meta-item">
                    <span className="meta-icon">📄</span>
                    {ws.stats?.total_files ?? 0} files
                  </span>
                  <span className="meta-item">
                    <span className="meta-icon">🧠</span>
                    {ws.stats?.total_memories ?? 0} memories
                  </span>
                  <span className="meta-item">
                    <span className="meta-icon">🔧</span>
                    {ws.stats?.total_skills ?? 0} skills
                  </span>
                </div>
                <div className="workspace-meta-right">
                  <span className="meta-time">
                    Last activity: {ws.stats?.last_activity ? formatTime(ws.stats.last_activity) : 'N/A'}
                  </span>
                  <span className="meta-time">
                    Created: {formatTime(ws.created_at)}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <style>{styles}</style>
    </div>
  );
};

const styles = `
.panel-container { padding: 24px; max-width: 1400px; margin: 0 auto; }
.panel-header h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; color: var(--text, #1f2937); }
.panel-subtitle { color: var(--text-secondary, #6b7280); margin-bottom: 24px; font-size: 0.9rem; }
.panel-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 0; color: var(--text-secondary, #9ca3af); gap: 16px; font-size: 0.95rem; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--border, #e5e7eb); border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-banner { background: #fef2f2; color: #991b1b; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; }
.panel-empty { text-align: center; padding: 40px 0; color: var(--text-secondary, #9ca3af); }
.panel-empty p { font-size: 0.9rem; margin-bottom: 4px; }

.stats-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-item { flex: 1; min-width: 140px; background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 14px 18px; display: flex; align-items: center; gap: 12px; }
.stat-icon { font-size: 1.5rem; }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: 1.3rem; font-weight: 800; color: var(--text, #1f2937); }
.stat-label { font-size: 0.72rem; color: var(--text-secondary, #6b7280); font-weight: 600; }

.action-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.btn-primary-sm { padding: 8px 16px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-primary-sm:hover { background: #2563eb; }
.btn-secondary-sm { padding: 8px 16px; background: var(--bg-card, #fff); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-secondary-sm:hover { border-color: #3b82f6; color: #3b82f6; }

.workspace-list { display: flex; flex-direction: column; gap: 12px; }
.workspace-card { background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 18px 20px; transition: all 0.15s; }
.workspace-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.workspace-card.active { border-color: #86efac; background: #f0fdf4; }
.workspace-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.workspace-title-row { display: flex; align-items: center; gap: 8px; }
.active-dot { width: 10px; height: 10px; border-radius: 50%; background: #22c55e; flex-shrink: 0; box-shadow: 0 0 6px rgba(34, 197, 94, 0.5); }
.workspace-name { font-size: 1rem; font-weight: 700; color: var(--text, #1f2937); margin: 0; }
.active-badge { font-size: 0.65rem; font-weight: 700; background: #22c55e; color: #fff; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; }
.workspace-card-actions { display: flex; gap: 6px; flex-shrink: 0; }
.workspace-description { font-size: 0.85rem; color: var(--text-secondary, #6b7280); margin-bottom: 12px; line-height: 1.4; }
.workspace-meta-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.workspace-meta { display: flex; gap: 16px; flex-wrap: wrap; }
.meta-item { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: var(--text-secondary, #6b7280); }
.meta-icon { font-size: 0.85rem; }
.workspace-meta-right { display: flex; gap: 16px; flex-wrap: wrap; }
.meta-time { font-size: 0.75rem; color: var(--text-secondary, #9ca3af); }

.btn-mini { padding: 4px 10px; background: var(--bg-card, #f3f4f6); border: 1px solid var(--border, #d1d5db); border-radius: 6px; font-size: 0.72rem; cursor: pointer; color: var(--text, #374151); transition: all 0.15s; white-space: nowrap; }
.btn-mini:hover { border-color: #3b82f6; color: #3b82f6; }
.btn-mini.danger { color: #dc2626; border-color: #fecaca; background: #fef2f2; }
.btn-mini.danger:hover { background: #fee2e2; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text, #374151); }
.form-group input, .form-group textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.9rem; background: var(--bg-card, #fff); color: var(--text, #1f2937); font-family: inherit; }
.form-group textarea { resize: vertical; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--bg-card, #fff); border-radius: 16px; padding: 28px; width: 90%; max-width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 20px; color: var(--text, #1f2937); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.btn-primary { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { padding: 10px 20px; background: var(--bg-card, #f3f4f6); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-danger { padding: 10px 20px; background: #ef4444; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-danger:hover { background: #dc2626; }
`;

export default WorkspacePanel;