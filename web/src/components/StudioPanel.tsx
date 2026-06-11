import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { StudioInfoItem, StudioTemplate, StudioMemoryEntry, StudioSnapshot, StudioStats } from '../types';

const CATEGORY_EMOJIS: Record<string, string> = {
  fact: '📌', preference: '⭐', relationship: '🔗', goal: '🎯',
  experience: '💡', context: '📋', system: '⚙️',
};

const IMPORTANCE_COLORS: Record<string, string> = {
  critical: '#dc2626', high: '#f59e0b', medium: '#6366f1', low: '#9ca3af', trivial: '#d1d5db',
};

export const StudioPanel: React.FC = () => {
  const [studios, setStudios] = useState<StudioInfoItem[]>([]);
  const [templates, setTemplates] = useState<StudioTemplate[]>([]);
  const [stats, setStats] = useState<StudioStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedStudio, setSelectedStudio] = useState<string | null>(null);
  const [memoryEntries, setMemoryEntries] = useState<StudioMemoryEntry[]>([]);
  const [snapshots, setSnapshots] = useState<StudioSnapshot[]>([]);
  const [memoryStats, setMemoryStats] = useState<Record<string, unknown> | null>(null);
  const [showAddMemory, setShowAddMemory] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [tab, setTab] = useState<'memory' | 'snapshots'>('memory');

  const [newStudio, setNewStudio] = useState({ name: '', description: '', template_id: '', icon: '📁' });
  const [newMemory, setNewMemory] = useState({ key: '', value: '', category: 'fact', importance: 'medium' });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [studioRes, statsRes] = await Promise.all([
        api.studios.list(),
        api.studios.stats(),
      ]);
      setStudios(studioRes.studios);
      setTemplates(studioRes.templates);
      setStats(statsRes);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load studios');
    } finally {
      setLoading(false);
    }
  };

  const loadStudioDetail = async (studioId: string) => {
    setSelectedStudio(studioId);
    try {
      const [memRes, snapRes] = await Promise.all([
        api.studios.memory.list(studioId, categoryFilter || undefined, searchQuery || undefined),
        api.studios.snapshots.list(studioId),
      ]);
      setMemoryEntries(memRes.entries);
      setMemoryStats(memRes.stats);
      setSnapshots(snapRes.snapshots || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    if (selectedStudio) {
      loadStudioDetail(selectedStudio);
    }
  }, [categoryFilter, searchQuery]);

  const handleCreate = async () => {
    if (!newStudio.name.trim()) return;
    try {
      await api.studios.create(newStudio);
      setShowCreate(false);
      setNewStudio({ name: '', description: '', template_id: '', icon: '📁' });
      loadData();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async (id: string) => {
    try { await api.studios.delete(id); setSelectedStudio(null); loadData(); } catch (e: any) { setError(e.message); }
  };

  const handleAddMemory = async () => {
    if (!selectedStudio || !newMemory.key.trim() || !newMemory.value.trim()) return;
    try {
      await api.studios.memory.create(selectedStudio, newMemory);
      setShowAddMemory(false);
      setNewMemory({ key: '', value: '', category: 'fact', importance: 'medium' });
      loadStudioDetail(selectedStudio);
    } catch (e: any) { setError(e.message); }
  };

  const handleDeleteMemory = async (entryId: string) => {
    if (!selectedStudio) return;
    try { await api.studios.memory.delete(selectedStudio, entryId); loadStudioDetail(selectedStudio); } catch (e: any) { setError(e.message); }
  };

  const handlePinMemory = async (entryId: string) => {
    if (!selectedStudio) return;
    try { await api.studios.memory.pin(selectedStudio, entryId); loadStudioDetail(selectedStudio); } catch (e: any) { setError(e.message); }
  };

  const handleCreateSnapshot = async () => {
    if (!selectedStudio) return;
    try { await api.studios.snapshots.create(selectedStudio); loadStudioDetail(selectedStudio); } catch (e: any) { setError(e.message); }
  };

  const handleRollback = async (snapshotId: string) => {
    if (!selectedStudio) return;
    try { await api.studios.snapshots.rollback(selectedStudio, snapshotId); loadStudioDetail(selectedStudio); } catch (e: any) { setError(e.message); }
  };

  const getCategoryEmoji = (cat: string) => CATEGORY_EMOJIS[cat] || '📄';
  const getImportanceColor = (imp: string) => IMPORTANCE_COLORS[imp] || '#9ca3af';
  const formatTime = (iso: string) => iso ? new Date(iso).toLocaleString() : 'N/A';

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header"><h2>Buddy Studio</h2><p className="panel-subtitle">Project Workspace with White-Box Memory</p></div>
        <div className="panel-loading"><div className="spinner" /><span>Loading studios...</span></div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Buddy Studio</h2>
        <p className="panel-subtitle">Project Workspace with White-Box Memory</p>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-icon">📁</span>
            <div className="stat-content"><span className="stat-value">{stats.total_studios}</span><span className="stat-label">Studios</span></div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">🧠</span>
            <div className="stat-content"><span className="stat-value">{stats.total_memory_entries}</span><span className="stat-label">Memory Entries</span></div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">📸</span>
            <div className="stat-content"><span className="stat-value">{stats.total_snapshots}</span><span className="stat-label">Snapshots</span></div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="action-bar">
        <button className="btn-primary-sm" onClick={() => setShowCreate(true)}>+ New Studio</button>
        <button className="btn-secondary-sm" onClick={loadData}>🔄 Refresh</button>
      </div>

      {/* Templates */}
      {templates.length > 0 && (
        <div className="templates-section">
          <h4 className="section-label">Templates</h4>
          <div className="template-chips">
            {templates.map(t => (
              <span key={t.id} className="template-chip" onClick={() => setNewStudio({ ...newStudio, template_id: t.id, icon: t.icon, name: t.name })}>
                {t.icon} {t.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create Studio</h3>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={newStudio.name} onChange={e => setNewStudio({ ...newStudio, name: e.target.value })} placeholder="Studio name" autoFocus />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea rows={2} value={newStudio.description} onChange={e => setNewStudio({ ...newStudio, description: e.target.value })} placeholder="What is this studio about?" />
            </div>
            <div className="form-group">
              <label>Template</label>
              <select value={newStudio.template_id} onChange={e => setNewStudio({ ...newStudio, template_id: e.target.value })}>
                <option value="">None</option>
                {templates.map(t => <option key={t.id} value={t.id}>{t.icon} {t.name}</option>)}
              </select>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Studio Grid */}
      <div className="studio-layout">
        <div className="studio-list">
          <h4 className="section-label">Workspaces</h4>
          {studios.map(s => (
            <div
              key={s.id}
              className={`studio-list-item ${selectedStudio === s.id ? 'active' : ''}`}
              onClick={() => loadStudioDetail(s.id)}
            >
              <span className="studio-item-icon">{s.icon}</span>
              <div className="studio-item-info">
                <span className="studio-item-name">{s.name}</span>
                <span className="studio-item-meta">{s.memory_entry_count} entries · {s.snapshot_count} snapshots</span>
              </div>
              <button className="studio-item-delete" onClick={e => { e.stopPropagation(); handleDelete(s.id); }}>×</button>
            </div>
          ))}
          {studios.length === 0 && <div className="panel-empty"><p>No studios yet</p></div>}
        </div>

        {/* Studio Detail */}
        {selectedStudio && (
          <div className="studio-detail">
            <div className="detail-tabs">
              <button className={`detail-tab ${tab === 'memory' ? 'active' : ''}`} onClick={() => setTab('memory')}>Memory</button>
              <button className={`detail-tab ${tab === 'snapshots' ? 'active' : ''}`} onClick={() => setTab('snapshots')}>Snapshots</button>
            </div>

            {tab === 'memory' && (
              <div className="memory-section">
                <div className="memory-actions">
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search memories..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                  />
                  <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
                    <option value="">All Categories</option>
                    <option value="fact">Fact</option>
                    <option value="preference">Preference</option>
                    <option value="relationship">Relationship</option>
                    <option value="goal">Goal</option>
                    <option value="experience">Experience</option>
                  </select>
                  <button className="btn-primary-sm" onClick={() => setShowAddMemory(true)}>+ Add Memory</button>
                </div>
                {memoryStats && (
                  <div className="memory-mini-stats">
                    <span>Total: <strong>{String(memoryStats.total_entries || 0)}</strong></span>
                    <span>Pinned: <strong>{String(memoryStats.pinned || 0)}</strong></span>
                  </div>
                )}
                <div className="memory-grid">
                  {memoryEntries.map(entry => (
                    <div key={entry.id} className={`memory-card ${entry.is_pinned ? 'pinned' : ''}`}>
                      <div className="memory-card-header">
                        <span className="memory-key">{getCategoryEmoji(entry.category)} {entry.key}</span>
                        <span className="memory-importance" style={{ color: getImportanceColor(entry.importance) }}>● {entry.importance}</span>
                      </div>
                      <div className="memory-value">{entry.value}</div>
                      {entry.tags?.length > 0 && (
                        <div className="memory-tags">
                          {entry.tags.map(t => <span key={t} className="memory-tag">{t}</span>)}
                        </div>
                      )}
                      <div className="memory-meta-row">
                        <span className="memory-meta">v{entry.version} · {entry.confidence ? `${(entry.confidence * 100).toFixed(0)}%` : ''}</span>
                      </div>
                      <div className="memory-card-actions">
                        <button className="btn-mini" onClick={() => handlePinMemory(entry.id)}>{entry.is_pinned ? '📌 Unpin' : '📌 Pin'}</button>
                        <button className="btn-mini danger" onClick={() => handleDeleteMemory(entry.id)}>× Delete</button>
                      </div>
                    </div>
                  ))}
                  {memoryEntries.length === 0 && <div className="panel-empty"><p>No memories yet</p></div>}
                </div>
              </div>
            )}

            {tab === 'snapshots' && (
              <div className="snapshot-section">
                <button className="btn-primary-sm" onClick={handleCreateSnapshot}>+ Create Snapshot</button>
                <div className="snapshot-grid">
                  {snapshots.map(snap => (
                    <div key={snap.snapshot_id} className="snapshot-card">
                      <div className="snapshot-label">{snap.label}</div>
                      <div className="snapshot-meta">{snap.entry_count} entries · {formatTime(snap.created_at)}</div>
                      {snap.description && <div className="snapshot-desc">{snap.description}</div>}
                      <button className="btn-mini" onClick={() => handleRollback(snap.snapshot_id)}>↩ Rollback</button>
                    </div>
                  ))}
                  {snapshots.length === 0 && <div className="panel-empty"><p>No snapshots yet</p></div>}
                </div>
              </div>
            )}

            {/* Add Memory Modal */}
            {showAddMemory && (
              <div className="modal-overlay" onClick={() => setShowAddMemory(false)}>
                <div className="modal" onClick={e => e.stopPropagation()}>
                  <h3>Add Memory Entry</h3>
                  <div className="form-group">
                    <label>Key</label>
                    <input type="text" value={newMemory.key} onChange={e => setNewMemory({ ...newMemory, key: e.target.value })} placeholder="Memory key" autoFocus />
                  </div>
                  <div className="form-group">
                    <label>Value</label>
                    <textarea rows={3} value={newMemory.value} onChange={e => setNewMemory({ ...newMemory, value: e.target.value })} placeholder="Memory value" />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Category</label>
                      <select value={newMemory.category} onChange={e => setNewMemory({ ...newMemory, category: e.target.value })}>
                        <option value="fact">Fact</option>
                        <option value="preference">Preference</option>
                        <option value="relationship">Relationship</option>
                        <option value="goal">Goal</option>
                        <option value="experience">Experience</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Importance</label>
                      <select value={newMemory.importance} onChange={e => setNewMemory({ ...newMemory, importance: e.target.value })}>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                        <option value="trivial">Trivial</option>
                      </select>
                    </div>
                  </div>
                  <div className="modal-actions">
                    <button className="btn-secondary" onClick={() => setShowAddMemory(false)}>Cancel</button>
                    <button className="btn-primary" onClick={handleAddMemory}>Add</button>
                  </div>
                </div>
              </div>
            )}
          </div>
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

.section-label { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary, #6b7280); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }

.templates-section { margin-bottom: 20px; }
.template-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.template-chip { padding: 6px 14px; background: var(--bg-card, #fff); border: 1px solid var(--border, #d1d5db); border-radius: 20px; font-size: 0.82rem; cursor: pointer; color: var(--text, #374151); transition: all 0.15s; }
.template-chip:hover { border-color: #3b82f6; color: #3b82f6; transform: translateY(-1px); }

.studio-layout { display: flex; gap: 24px; }
.studio-list { flex: 0 0 300px; border-right: 1px solid var(--border, #e5e7eb); padding-right: 20px; }
.studio-list-item { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-radius: 10px; cursor: pointer; transition: all 0.15s; margin-bottom: 4px; border: 1px solid transparent; }
.studio-list-item:hover { background: var(--bg-card, #f9fafb); border-color: var(--border, #d1d5db); }
.studio-list-item.active { background: #eff6ff; border-color: #93c5fd; }
.studio-item-icon { font-size: 1.3rem; }
.studio-item-info { display: flex; flex-direction: column; flex: 1; }
.studio-item-name { font-weight: 600; font-size: 0.9rem; color: var(--text, #1f2937); }
.studio-item-meta { font-size: 0.75rem; color: var(--text-secondary, #9ca3af); }
.studio-item-delete { background: none; border: none; color: #d1d5db; cursor: pointer; font-size: 1.1rem; padding: 2px 6px; }
.studio-item-delete:hover { color: #ef4444; }

.studio-detail { flex: 1; min-width: 0; }
.detail-tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 2px solid var(--border, #e5e7eb); }
.detail-tab { padding: 10px 20px; background: none; border: none; font-size: 0.9rem; font-weight: 600; color: var(--text-secondary, #6b7280); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.15s; }
.detail-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
.detail-tab:hover { color: var(--text, #374151); }

.memory-section { }
.memory-actions { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.search-input { padding: 8px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.85rem; flex: 1; min-width: 150px; background: var(--bg-card, #fff); color: var(--text, #1f2937); }
.memory-actions select { padding: 8px 10px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.85rem; background: var(--bg-card, #fff); color: var(--text, #374151); }
.memory-mini-stats { display: flex; gap: 16px; margin-bottom: 14px; font-size: 0.8rem; color: var(--text-secondary, #6b7280); }

.memory-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.memory-card { background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 10px; padding: 14px; transition: box-shadow 0.15s; }
.memory-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.memory-card.pinned { border-color: #fbbf24; background: #fffbeb; }
.memory-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.memory-key { font-weight: 700; font-size: 0.85rem; color: var(--text, #1f2937); }
.memory-importance { font-size: 0.7rem; font-weight: 700; text-transform: capitalize; }
.memory-value { font-size: 0.82rem; color: var(--text-secondary, #4b5563); margin-bottom: 8px; line-height: 1.4; word-break: break-word; }
.memory-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }
.memory-tag { padding: 2px 8px; background: var(--bg-card, #f3f4f6); border-radius: 12px; font-size: 0.7rem; color: var(--text-secondary, #6b7280); }
.memory-meta-row { margin-bottom: 8px; }
.memory-meta { font-size: 0.7rem; color: var(--text-secondary, #9ca3af); }
.memory-card-actions { display: flex; gap: 6px; }
.btn-mini { padding: 4px 10px; background: var(--bg-card, #f3f4f6); border: 1px solid var(--border, #d1d5db); border-radius: 6px; font-size: 0.72rem; cursor: pointer; color: var(--text, #374151); transition: all 0.15s; }
.btn-mini:hover { border-color: #3b82f6; color: #3b82f6; }
.btn-mini.danger { color: #dc2626; border-color: #fecaca; background: #fef2f2; }
.btn-mini.danger:hover { background: #fee2e2; }

.snapshot-section { }
.snapshot-section .btn-primary-sm { margin-bottom: 16px; }
.snapshot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.snapshot-card { background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 10px; padding: 14px; }
.snapshot-label { font-weight: 700; font-size: 0.9rem; color: var(--text, #1f2937); margin-bottom: 6px; }
.snapshot-meta { font-size: 0.75rem; color: var(--text-secondary, #6b7280); margin-bottom: 4px; }
.snapshot-desc { font-size: 0.8rem; color: var(--text-secondary, #4b5563); margin-bottom: 10px; }
.snapshot-card .btn-mini { margin-top: 4px; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text, #374151); }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.9rem; background: var(--bg-card, #fff); color: var(--text, #1f2937); font-family: inherit; }
.form-group textarea { resize: vertical; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--bg-card, #fff); border-radius: 16px; padding: 28px; width: 90%; max-width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 20px; color: var(--text, #1f2937); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.btn-primary { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { padding: 10px 20px; background: var(--bg-card, #f3f4f6); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
`;

export default StudioPanel;