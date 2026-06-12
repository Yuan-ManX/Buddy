import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

interface MemoryEntry {
  id: string;
  content: string;
  memory_type: string;
  importance: string;
  workspace_id?: string;
  agent_id?: string;
  tags: string[];
  is_pinned: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

interface WhiteboxStats {
  total_entries: number;
  pinned_entries: number;
  by_type: Record<string, number>;
  by_importance: Record<string, number>;
  memory_types: string[];
  importances: string[];
}

const TYPE_EMOJIS: Record<string, string> = {
  episodic: '�',
  semantic: '💡',
  procedural: '⚙️',
  decision: '🎯',
  preference: '⭐',
};

const IMPORTANCE_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#9ca3af',
  trivial: '#e5e7eb',
};

export const WhiteboxMemoryPanel: React.FC = () => {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [stats, setStats] = useState<WhiteboxStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<MemoryEntry | null>(null);
  const [showEdit, setShowEdit] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [importanceFilter, setImportanceFilter] = useState<string>('');
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showAudit, setShowAudit] = useState<string | null>(null);
  const [auditTrail, setAuditTrail] = useState<any[]>([]);
  const [detailEntry, setDetailEntry] = useState<MemoryEntry | null>(null);
  const { success: showSuccess, error: showError } = useToast();

  const [newEntry, setNewEntry] = useState({
    content: '',
    memory_type: 'semantic',
    importance: 'medium',
    workspace_id: '',
    agent_id: '',
    tags: [] as string[],
  });

  useEffect(() => {
    loadData();
  }, [typeFilter, importanceFilter, pinnedOnly]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [entriesRes, statsRes] = await Promise.all([
        api.whiteboxMemory.listEntries({
          memory_type: typeFilter || undefined,
          importance: importanceFilter || undefined,
          pinned_only: pinnedOnly || undefined,
          limit: 200,
        }),
        api.whiteboxMemory.stats(),
      ]);
      const mapped = (entriesRes.entries as unknown as MemoryEntry[]).map(e => ({
        ...e,
        tags: e.tags || [],
        is_pinned: e.is_pinned || false,
      }));
      setEntries(mapped);
      setStats(statsRes as unknown as WhiteboxStats);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load whitebox memory');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newEntry.content.trim()) return;
    try {
      await api.whiteboxMemory.createEntry(newEntry);
      setShowCreate(false);
      setNewEntry({ content: '', memory_type: 'semantic', importance: 'medium', workspace_id: '', agent_id: '', tags: [] });
      showSuccess('Memory entry created');
      loadData();
    } catch (e: any) {
      showError('Failed to create entry');
    }
  };

  const handleEdit = async () => {
    if (!selectedEntry || !editContent.trim()) return;
    try {
      await api.whiteboxMemory.editContent(selectedEntry.id, editContent);
      setShowEdit(false);
      showSuccess('Memory entry updated');
      loadData();
    } catch (e: any) {
      showError('Failed to edit entry');
    }
  };

  const handleDelete = async (entry: MemoryEntry) => {
    if (!confirm('Delete this memory entry?')) return;
    try {
      await api.whiteboxMemory.deleteEntry(entry.id);
      showSuccess('Memory entry deleted');
      loadData();
    } catch (e: any) {
      showError('Failed to delete entry');
    }
  };

  const handlePin = async (entry: MemoryEntry) => {
    try {
      if (entry.is_pinned) {
        await api.whiteboxMemory.unpinEntry(entry.id);
        showSuccess('Memory entry unpinned');
      } else {
        await api.whiteboxMemory.pinEntry(entry.id);
        showSuccess('Memory entry pinned');
      }
      loadData();
    } catch (e: any) {
      showError('Failed to toggle pin');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadData();
      return;
    }
    try {
      setIsSearching(true);
      const res = await api.whiteboxMemory.search(searchQuery);
      const results = (res.results as unknown as MemoryEntry[]).map(e => ({
        ...e,
        tags: e.tags || [],
        is_pinned: e.is_pinned || false,
      }));
      setEntries(results);
    } catch (e: any) {
      showError('Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleRunDream = async () => {
    try {
      await api.whiteboxMemory.runDream();
      showSuccess('Dream cycle completed');
      loadData();
    } catch (e: any) {
      showError('Dream cycle failed');
    }
  };

  const handleRollbackDream = async () => {
    if (!confirm('Roll back the last dream cycle? This will undo recent memory changes.')) return;
    try {
      await api.whiteboxMemory.rollbackDream();
      showSuccess('Dream cycle rolled back');
      loadData();
    } catch (e: any) {
      showError('Rollback failed');
    }
  };

  // ── Batch Operations ──

  const toggleBatchMode = () => {
    setBatchMode(!batchMode);
    setSelectedIds(new Set());
  };

  const toggleSelectEntry = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const batchDelete = async () => {
    if (!selectedIds.size) return;
    if (!confirm(`Delete ${selectedIds.size} selected entries?`)) return;
    try {
      for (const id of Array.from(selectedIds)) {
        await api.whiteboxMemory.deleteEntry(id);
      }
      showSuccess(`${selectedIds.size} entries deleted`);
      setBatchMode(false);
      setSelectedIds(new Set());
      loadData();
    } catch (e: any) {
      showError('Batch delete failed');
    }
  };

  const batchPin = async () => {
    if (!selectedIds.size) return;
    try {
      for (const id of Array.from(selectedIds)) {
        await api.whiteboxMemory.pinEntry(id);
      }
      showSuccess(`${selectedIds.size} entries pinned`);
      setBatchMode(false);
      setSelectedIds(new Set());
      loadData();
    } catch (e: any) {
      showError('Batch pin failed');
    }
  };

  // ── Audit Trail ──

  const handleViewAudit = async (entry: MemoryEntry) => {
    if (showAudit === entry.id) {
      setShowAudit(null);
      return;
    }
    try {
      const res = await api.whiteboxMemory.getAuditTrail(entry.id) as any;
      setAuditTrail(res.trail || res.audit_trail || []);
      setShowAudit(entry.id);
    } catch (e: any) {
      showError('Failed to load audit trail');
    }
  };

  // ── Export ──

  const handleExport = async (format: string = 'json') => {
    try {
      const res = await api.whiteboxMemory.export(format) as any;
      const data = JSON.stringify(res, null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `buddy-whitebox-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showSuccess('Export downloaded');
    } catch (e: any) {
      showError('Export failed');
    }
  };

  // ── Detail View ──

  const handleViewDetail = (entry: MemoryEntry) => {
    setDetailEntry(detailEntry?.id === entry.id ? null : entry);
  };

  const openEdit = (entry: MemoryEntry) => {
    setSelectedEntry(entry);
    setEditContent(entry.content);
    setShowEdit(true);
  };

  if (loading && !entries.length) {
    return <div className="panel-loading">Loading whitebox memory...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Whitebox Memory</h2>
        <div className="panel-header-actions">
          <button className="btn-secondary" onClick={() => handleExport('json')}>
            📥 Export
          </button>
          <button className={`btn-secondary ${batchMode ? 'active' : ''}`} onClick={toggleBatchMode}>
            {batchMode ? '✕ Cancel' : '☐ Batch'}
          </button>
          <button className="btn-secondary" onClick={handleRunDream}>
            🌙 Dream
          </button>
          <button className="btn-secondary" onClick={handleRollbackDream}>
            ↩ Rollback
          </button>
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + New Entry
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="board-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_entries}</span>
            <span className="stat-label">Total Entries</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.pinned_entries || 0}</span>
            <span className="stat-label">Pinned</span>
          </div>
          {stats.by_importance && Object.entries(stats.by_importance).slice(0, 3).map(([imp, count]) => (
            <div key={imp} className="stat-card">
              <span className="stat-value">{count}</span>
              <span className="stat-label" style={{ color: IMPORTANCE_COLORS[imp] }}>{imp}</span>
            </div>
          ))}
        </div>
      )}

      <div className="filters-row">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search entries..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button className="btn-secondary" onClick={handleSearch} disabled={isSearching}>
            {isSearching ? '...' : 'Search'}
          </button>
        </div>
        <div className="filter-group">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Types</option>
            {stats?.memory_types?.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select
            value={importanceFilter}
            onChange={(e) => setImportanceFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">All Importance</option>
            {stats?.importances?.map(i => (
              <option key={i} value={i}>{i}</option>
            ))}
          </select>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={pinnedOnly}
              onChange={(e) => setPinnedOnly(e.target.checked)}
            />
            Pinned Only
          </label>
        </div>
      </div>

      {batchMode && selectedIds.size > 0 && (
        <div className="batch-actions-bar">
          <span>{selectedIds.size} selected</span>
          <button className="btn-sm btn-primary" onClick={batchPin}>📌 Pin All</button>
          <button className="btn-sm btn-danger" onClick={batchDelete}>🗑 Delete All</button>
        </div>
      )}

      <div className="memory-entry-grid">
        {entries.map(entry => (
          <div
            key={entry.id}
            className={`memory-entry-card ${entry.is_pinned ? 'pinned' : ''} ${showAudit === entry.id ? 'expanded' : ''}`}
          >
            <div className="memory-entry-header">
              {batchMode && (
                <input
                  type="checkbox"
                  checked={selectedIds.has(entry.id)}
                  onChange={() => toggleSelectEntry(entry.id)}
                  className="batch-checkbox"
                />
              )}
              <span className="memory-type-badge">
                {TYPE_EMOJIS[entry.memory_type] || '📝'} {entry.memory_type}
              </span>
              <span
                className="importance-badge"
                style={{ backgroundColor: IMPORTANCE_COLORS[entry.importance] || '#9ca3af' }}
              >
                {entry.importance}
              </span>
              {entry.is_pinned && <span className="pinned-badge">📌</span>}
            </div>
            <div className="memory-entry-content">
              {entry.content.length > 200
                ? entry.content.slice(0, 200) + '...'
                : entry.content}
            </div>
            {entry.tags?.length > 0 && (
              <div className="tag-list">
                {entry.tags.map((tag, idx) => (
                  <span key={idx} className="tag">{tag}</span>
                ))}
              </div>
            )}
            <div className="memory-entry-meta">
              {entry.workspace_id && (
                <span title="Workspace">📂 {entry.workspace_id.slice(0, 8)}</span>
              )}
              {entry.agent_id && (
                <span title="Agent">👤 {entry.agent_id.slice(0, 8)}</span>
              )}
              <span title="Version">v{entry.version || 1}</span>
              <span title="Created">{new Date(entry.created_at).toLocaleDateString()}</span>
            </div>
            <div className="memory-entry-actions">
              <button className="btn-sm btn-secondary" onClick={() => handleViewDetail(entry)}>
                {detailEntry?.id === entry.id ? '▲ Less' : '▼ More'}
              </button>
              <button className="btn-sm btn-secondary" onClick={() => handleViewAudit(entry)}>
                {showAudit === entry.id ? '▲ Audit' : '📋 Audit'}
              </button>
              <button className="btn-sm btn-secondary" onClick={() => openEdit(entry)}>
                Edit
              </button>
              <button className="btn-sm btn-secondary" onClick={() => handlePin(entry)}>
                {entry.is_pinned ? '📌 Unpin' : '📌 Pin'}
              </button>
              <button className="btn-sm btn-danger" onClick={() => handleDelete(entry)}>
                Delete
              </button>
            </div>

            {/* Audit Trail Expansion */}
            {showAudit === entry.id && (
              <div className="audit-trail">
                <h4>Audit Trail</h4>
                {auditTrail.length === 0 ? (
                  <p className="hint">No audit events recorded.</p>
                ) : (
                  <div className="audit-list">
                    {auditTrail.map((event: any, i: number) => (
                      <div key={i} className="audit-item">
                        <span className="audit-action">{event.action || event.event || 'update'}</span>
                        <span className="audit-time">
                          {event.timestamp ? new Date(event.timestamp).toLocaleString() : ''}
                        </span>
                        {event.previous && (
                          <div className="audit-diff">
                            <span className="audit-label">Previous:</span>
                            {typeof event.previous === 'string'
                              ? event.previous.slice(0, 100)
                              : JSON.stringify(event.previous).slice(0, 100)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Detail View Expansion */}
            {detailEntry?.id === entry.id && (
              <div className="detail-view">
                <h4>Entry Details</h4>
                <div className="detail-grid">
                  <span className="detail-label">ID:</span>
                  <span className="detail-value">{entry.id}</span>
                  <span className="detail-label">Version:</span>
                  <span className="detail-value">v{entry.version || 1}</span>
                  <span className="detail-label">Created:</span>
                  <span className="detail-value">{new Date(entry.created_at).toLocaleString()}</span>
                  <span className="detail-label">Updated:</span>
                  <span className="detail-value">{new Date(entry.updated_at).toLocaleString()}</span>
                  {entry.workspace_id && (
                    <>
                      <span className="detail-label">Workspace:</span>
                      <span className="detail-value">{entry.workspace_id}</span>
                    </>
                  )}
                  {entry.agent_id && (
                    <>
                      <span className="detail-label">Agent:</span>
                      <span className="detail-value">{entry.agent_id}</span>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        {entries.length === 0 && (
          <div className="panel-empty">No memory entries. Create one to build the memory graph.</div>
        )}
      </div>

      {/* Create Entry Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>New Memory Entry</h2>
            <div className="form-group">
              <label>Content</label>
              <textarea
                placeholder="Memory content..."
                value={newEntry.content}
                onChange={(e) => setNewEntry({ ...newEntry, content: e.target.value })}
                rows={4}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Memory Type</label>
              <select
                value={newEntry.memory_type}
                onChange={(e) => setNewEntry({ ...newEntry, memory_type: e.target.value })}
              >
                <option value="episodic">Episodic</option>
                <option value="semantic">Semantic</option>
                <option value="procedural">Procedural</option>
                <option value="decision">Decision</option>
                <option value="preference">Preference</option>
              </select>
            </div>
            <div className="form-group">
              <label>Importance</label>
              <select
                value={newEntry.importance}
                onChange={(e) => setNewEntry({ ...newEntry, importance: e.target.value })}
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="trivial">Trivial</option>
              </select>
            </div>
            <div className="form-group">
              <label>Workspace ID (optional)</label>
              <input
                type="text"
                placeholder="workspace-id"
                value={newEntry.workspace_id}
                onChange={(e) => setNewEntry({ ...newEntry, workspace_id: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Agent ID (optional)</label>
              <input
                type="text"
                placeholder="agent-id"
                value={newEntry.agent_id}
                onChange={(e) => setNewEntry({ ...newEntry, agent_id: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                placeholder="tag1, tag2, tag3"
                onChange={(e) => setNewEntry({
                  ...newEntry,
                  tags: e.target.value.split(',').map(t => t.trim()).filter(t => t),
                })}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleCreate}>
                Create Entry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Entry Modal */}
      {showEdit && selectedEntry && (
        <div className="modal-overlay" onClick={() => setShowEdit(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Edit Memory Entry</h2>
            <div className="memory-meta-info">
              <span>Type: {selectedEntry.memory_type}</span>
              <span>Importance: {selectedEntry.importance}</span>
              <span>Version: {selectedEntry.version || 1}</span>
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={6}
                autoFocus
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowEdit(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleEdit}>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};