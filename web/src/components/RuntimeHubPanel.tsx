import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { RuntimeItem, RuntimeHubStats } from '../types';

const BACKEND_EMOJIS: Record<string, string> = {
  local: '💻',
  docker: '🐳',
  venv: '📦',
};

const STATUS_COLORS: Record<string, string> = {
  ready: '#10b981',
  idle: '#6366f1',
  running: '#f59e0b',
  error: '#ef4444',
  hibernating: '#9ca3af',
};

export const RuntimeHubPanel: React.FC = () => {
  const [runtimes, setRuntimes] = useState<RuntimeItem[]>([]);
  const [stats, setStats] = useState<RuntimeHubStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showExecute, setShowExecute] = useState<string | null>(null);
  const [newRuntime, setNewRuntime] = useState({ name: '', backend: 'local', image: '' });
  const [execForm, setExecForm] = useState({ command: '', code: '', language: 'python', timeout_sec: 300 });
  const [execResult, setExecResult] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [rtRes, statsRes] = await Promise.all([
        api.runtimes.list(),
        api.runtimes.stats(),
      ]);
      setRuntimes(rtRes.runtimes);
      setStats(statsRes);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load runtime data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newRuntime.name.trim()) return;
    try {
      await api.runtimes.create(newRuntime);
      setShowCreate(false);
      setNewRuntime({ name: '', backend: 'local', image: '' });
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.runtimes.delete(id);
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleExecute = async (runtimeId: string) => {
    try {
      const result = await api.runtimes.execute({
        runtime_id: runtimeId,
        ...execForm,
      });
      setExecResult(JSON.stringify(result, null, 2));
    } catch (e: any) {
      setExecResult(`Error: ${e.message}`);
    }
  };

  const handleDiscover = async () => {
    try {
      await api.runtimes.discover();
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const getBackendEmoji = (backend: string) => BACKEND_EMOJIS[backend] || '🖥️';
  const getStatusColor = (status: string) => STATUS_COLORS[status] || '#6b7280';
  const formatTime = (iso: string) => iso ? new Date(iso).toLocaleString() : 'N/A';

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header"><h2>Runtime Hub</h2><p className="panel-subtitle">Universal Execution Environment Management</p></div>
        <div className="panel-loading"><div className="spinner" /><span>Loading runtimes...</span></div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Runtime Hub</h2>
        <p className="panel-subtitle">Universal Execution Environment Management</p>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-icon">🖧</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_runtimes}</span>
              <span className="stat-label">Total Runtimes</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">⚡</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_executions}</span>
              <span className="stat-label">Total Executions</span>
            </div>
          </div>
          {Object.entries(stats.runtimes_by_backend || {}).map(([backend, count]) => (
            <div key={backend} className="stat-item">
              <span className="stat-icon">{getBackendEmoji(backend)}</span>
              <div className="stat-content">
                <span className="stat-value">{String(count)}</span>
                <span className="stat-label">{backend}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Status Distribution */}
      {stats && Object.keys(stats.runtimes_by_status || {}).length > 0 && (
        <div className="status-chips">
          {Object.entries(stats.runtimes_by_status).map(([status, count]) => (
            <span key={status} className="status-chip" style={{ backgroundColor: getStatusColor(status), color: '#fff' }}>
              {status}: {String(count)}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="action-bar">
        <button className="btn-primary-sm" onClick={() => setShowCreate(true)}>+ New Runtime</button>
        <button className="btn-secondary-sm" onClick={handleDiscover}>🔍 Discover</button>
        <button className="btn-secondary-sm" onClick={loadData}>🔄 Refresh</button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create Runtime</h3>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={newRuntime.name} onChange={e => setNewRuntime({ ...newRuntime, name: e.target.value })} placeholder="Runtime name" autoFocus />
            </div>
            <div className="form-group">
              <label>Backend</label>
              <select value={newRuntime.backend} onChange={e => setNewRuntime({ ...newRuntime, backend: e.target.value })}>
                <option value="local">Local</option>
                <option value="docker">Docker</option>
                <option value="venv">Virtual Env</option>
              </select>
            </div>
            {newRuntime.backend === 'docker' && (
              <div className="form-group">
                <label>Docker Image</label>
                <input type="text" value={newRuntime.image} onChange={e => setNewRuntime({ ...newRuntime, image: e.target.value })} placeholder="e.g., python:3.11" />
              </div>
            )}
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Runtime Grid */}
      {runtimes.length > 0 ? (
        <div className="runtime-grid">
          {runtimes.map(rt => (
            <div key={rt.id} className="runtime-card">
              <div className="runtime-card-header">
                <span className="runtime-name">{getBackendEmoji(rt.backend)} {rt.name}</span>
                <span className="runtime-status" style={{ color: getStatusColor(rt.status) }}>● {rt.status}</span>
              </div>
              <div className="runtime-detail">
                <div className="runtime-meta"><span className="meta-label">Backend</span><span className="meta-value">{rt.backend}</span></div>
                <div className="runtime-meta"><span className="meta-label">Executions</span><span className="meta-value">{rt.execution_count}</span></div>
                <div className="runtime-meta"><span className="meta-label">Last Exec</span><span className="meta-value">{formatTime(rt.last_execution_at)}</span></div>
                {rt.tags?.length > 0 && (
                  <div className="runtime-meta"><span className="meta-label">Tags</span>
                    <div className="tag-chips">{rt.tags.map(t => <span key={t} className="tag-chip">{t}</span>)}</div>
                  </div>
                )}
              </div>
              <div className="runtime-card-actions">
                <button className="btn-secondary-sm" onClick={() => { setShowExecute(rt.id); setExecResult(null); }}>▶ Execute</button>
                <button className="btn-danger-sm" onClick={() => handleDelete(rt.id)}>Delete</button>
              </div>

              {/* Execute Panel */}
              {showExecute === rt.id && (
                <div className="exec-panel">
                  <h4>Execute in {rt.name}</h4>
                  <textarea
                    className="exec-textarea"
                    value={execForm.code}
                    onChange={e => setExecForm({ ...execForm, code: e.target.value, command: execForm.code ? execForm.command : '' })}
                    placeholder="Enter code to execute..."
                    rows={4}
                  />
                  <div className="exec-language-row">
                    <select value={execForm.language} onChange={e => setExecForm({ ...execForm, language: e.target.value })}>
                      <option value="python">Python</option>
                      <option value="bash">Bash</option>
                      <option value="javascript">JavaScript</option>
                    </select>
                    <button className="btn-primary-sm" onClick={() => handleExecute(rt.id)}>Run</button>
                  </div>
                  {execResult && (
                    <pre className="exec-result">{execResult}</pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="panel-empty">
          <span className="empty-icon">📡</span>
          <p>No runtimes registered yet</p>
          <p className="empty-hint">Create a runtime to manage execution environments.</p>
        </div>
      )}

      <style>{styles}</style>
    </div>
  );
};

const styles = `
.panel-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
.panel-header h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; color: var(--text, #1f2937); }
.panel-subtitle { color: var(--text-secondary, #6b7280); margin-bottom: 24px; font-size: 0.9rem; }
.panel-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 0; color: var(--text-secondary, #9ca3af); gap: 16px; font-size: 0.95rem; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--border, #e5e7eb); border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-banner { background: #fef2f2; color: #991b1b; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; }
.panel-empty { text-align: center; padding: 60px 0; color: var(--text-secondary, #9ca3af); }
.empty-icon { font-size: 3rem; display: block; margin-bottom: 12px; }
.panel-empty p { font-size: 0.95rem; margin-bottom: 6px; }
.empty-hint { font-size: 0.8rem; color: var(--text-secondary, #9ca3af); max-width: 400px; margin: 0 auto; line-height: 1.5; }

.stats-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-item { flex: 1; min-width: 140px; background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 14px 18px; display: flex; align-items: center; gap: 12px; }
.stat-icon { font-size: 1.5rem; }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: 1.3rem; font-weight: 800; color: var(--text, #1f2937); }
.stat-label { font-size: 0.72rem; color: var(--text-secondary, #6b7280); font-weight: 600; }

.status-chips { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.status-chip { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; text-transform: capitalize; }

.action-bar { display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; }
.btn-primary-sm { padding: 8px 16px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-primary-sm:hover { background: #2563eb; }
.btn-secondary-sm { padding: 8px 16px; background: var(--bg-card, #fff); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-secondary-sm:hover { border-color: #3b82f6; color: #3b82f6; }
.btn-danger-sm { padding: 6px 12px; background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.8rem; }
.btn-danger-sm:hover { background: #fee2e2; }

.runtime-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 16px; }
.runtime-card { background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 20px; transition: box-shadow 0.2s; }
.runtime-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.runtime-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--border, #f3f4f6); }
.runtime-name { font-weight: 700; font-size: 0.95rem; color: var(--text, #1f2937); }
.runtime-status { font-size: 0.8rem; font-weight: 700; text-transform: capitalize; }
.runtime-detail { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.runtime-meta { display: flex; justify-content: space-between; align-items: center; }
.meta-label { font-size: 0.8rem; color: var(--text-secondary, #6b7280); }
.meta-value { font-size: 0.8rem; font-weight: 600; color: var(--text, #374151); }
.tag-chips { display: flex; gap: 4px; flex-wrap: wrap; }
.tag-chip { padding: 2px 8px; background: var(--bg-card, #f3f4f6); border-radius: 12px; font-size: 0.7rem; color: var(--text-secondary, #4b5563); }
.runtime-card-actions { display: flex; gap: 8px; }

.exec-panel { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border, #f3f4f6); }
.exec-panel h4 { font-size: 0.9rem; font-weight: 700; margin-bottom: 10px; color: var(--text, #374151); }
.exec-textarea { width: 100%; padding: 10px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-family: monospace; font-size: 0.85rem; resize: vertical; background: var(--bg-card, #f9fafb); color: var(--text, #1f2937); }
.exec-language-row { display: flex; gap: 8px; margin-top: 8px; align-items: center; }
.exec-language-row select { padding: 6px 10px; border: 1px solid var(--border, #d1d5db); border-radius: 6px; font-size: 0.85rem; background: var(--bg-card, #fff); color: var(--text, #374151); }
.exec-result { margin-top: 10px; padding: 12px; background: var(--bg-card, #1f2937); color: #e5e7eb; border-radius: 8px; font-size: 0.8rem; overflow-x: auto; max-height: 300px; overflow-y: auto; white-space: pre-wrap; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--bg-card, #fff); border-radius: 16px; padding: 28px; width: 90%; max-width: 480px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 20px; color: var(--text, #1f2937); }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text, #374151); }
.form-group input, .form-group select { width: 100%; padding: 10px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.9rem; background: var(--bg-card, #fff); color: var(--text, #1f2937); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.btn-primary { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { padding: 10px 20px; background: var(--bg-card, #f3f4f6); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
`;

export default RuntimeHubPanel;