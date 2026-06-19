import React, { useState, useEffect } from 'react';

interface WhiteMemoryStats {
  total_entries: number;
  active_entries: number;
  archived_entries: number;
  pinned_entries: number;
  total_audits: number;
  entries_by_category: Record<string, number>;
  entries_by_importance: { high: number; medium: number; low: number };
  recent_audits: { audit_id: string; memory_id: string; stage: string; agent_id: string | null; trigger: string; timestamp: number }[];
}

interface WhiteMemoryEntry {
  entry_id: string;
  content: string;
  category: string;
  importance: number;
  confidence: number;
  pinned: boolean;
  tags: string[];
  version: number;
  access_count: number;
  workspace_id: string | null;
}

interface AuditEntry {
  audit_id: string;
  stage: string;
  agent_id: string | null;
  trigger: string;
  timestamp: number;
}

interface LineageEntry {
  entry_id: string;
  content: string;
  version: number;
  created_at: number;
}

export const WhiteMemoryPanel: React.FC = () => {
  const [stats, setStats] = useState<WhiteMemoryStats | null>(null);
  const [entries, setEntries] = useState<WhiteMemoryEntry[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<string | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [lineage, setLineage] = useState<LineageEntry[]>([]);
  const [showStore, setShowStore] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [formData, setFormData] = useState({ content: '', category: 'fact', importance: 0.5, confidence: 0.5, tags: '', workspace_id: '' });
  const [editData, setEditData] = useState({ entry_id: '', content: '', importance: 0.5, confidence: 0.5, tags: '' });
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchEntries();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/white-memory/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch white memory stats:', e); }
  };

  const fetchEntries = async (search?: string) => {
    try {
      const params = new URLSearchParams();
      if (search) params.set('search_text', search);
      params.set('limit', '50');
      const res = await fetch(`/api/white-memory/query?${params}`);
      const data = await res.json();
      setEntries(data.entries || []);
    } catch (e) { console.error('Failed to fetch entries:', e); }
  };

  const fetchAuditTrail = async (entryId: string) => {
    try {
      const res = await fetch(`/api/white-memory/audit/${entryId}`);
      const data = await res.json();
      setAuditTrail(data.audit_trail || []);
    } catch (e) { console.error('Failed to fetch audit trail:', e); }
  };

  const fetchLineage = async (entryId: string) => {
    try {
      const res = await fetch(`/api/white-memory/lineage/${entryId}`);
      const data = await res.json();
      setLineage(data.lineage || []);
    } catch (e) { console.error('Failed to fetch lineage:', e); }
  };

  const selectEntry = (entryId: string) => {
    setSelectedEntry(entryId === selectedEntry ? null : entryId);
    if (entryId !== selectedEntry) {
      fetchAuditTrail(entryId);
      fetchLineage(entryId);
    }
  };

  const storeMemory = async () => {
    setLoading(true);
    try {
      await fetch('/api/white-memory/store', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowStore(false);
      setFormData({ content: '', category: 'fact', importance: 0.5, confidence: 0.5, tags: '', workspace_id: '' });
      fetchStats();
      fetchEntries();
    } catch (e) { console.error('Store failed:', e); }
    setLoading(false);
  };

  const updateMemory = async () => {
    setLoading(true);
    try {
      await fetch('/api/white-memory/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...editData,
          tags: editData.tags.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowEdit(false);
      fetchStats();
      fetchEntries();
    } catch (e) { console.error('Update failed:', e); }
    setLoading(false);
  };

  const deleteMemory = async (entryId: string) => {
    await fetch('/api/white-memory/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId }),
    });
    fetchStats();
    fetchEntries();
  };

  const pinMemory = async (entryId: string) => {
    await fetch('/api/white-memory/pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId }),
    });
    fetchEntries();
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchEntries(searchQuery);
  };

  const categoryColor = (cat: string) => {
    const colors: Record<string, string> = {
      fact: '#3b82f6', preference: '#8b5cf6', decision: '#f59e0b',
      context: '#06b6d4', skill: '#16a34a', relationship: '#ec4899',
      insight: '#f97316',
    };
    return colors[cat] || '#9ca3af';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>White-box Memory</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Traceable memory management with full audit trail and version lineage</p>
        </div>
        <button onClick={() => setShowStore(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
          + Store Memory
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.active_entries}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active Entries</div>
          </div>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.pinned_entries}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Pinned</div>
          </div>
          <div style={{ flex: 1, background: '#f3f4f6', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#6b7280' }}>{stats.archived_entries}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Archived</div>
          </div>
          <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.total_audits}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Audit Records</div>
          </div>
        </div>
      )}

      {/* Search */}
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search memory entries..." style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
        <button type="submit" style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Search</button>
      </form>

      {/* Category Distribution */}
      {stats && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {Object.entries(stats.entries_by_category).map(([cat, count]) => (
            <span key={cat} style={{ background: `${categoryColor(cat)}15`, color: categoryColor(cat), padding: '4px 10px', borderRadius: 6, fontSize: 12, border: `1px solid ${categoryColor(cat)}30` }}>
              {cat}: {count}
            </span>
          ))}
        </div>
      )}

      {/* Store Form */}
      {showStore && (
        <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 16, border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Store New Memory Entry</h3>
          <textarea value={formData.content} onChange={e => setFormData({ ...formData, content: e.target.value })} placeholder="Memory content" rows={3} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', resize: 'vertical', marginBottom: 8 }} />
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <select value={formData.category} onChange={e => setFormData({ ...formData, category: e.target.value })} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }}>
              <option value="fact">Fact</option>
              <option value="preference">Preference</option>
              <option value="decision">Decision</option>
              <option value="context">Context</option>
              <option value="skill">Skill</option>
              <option value="relationship">Relationship</option>
              <option value="insight">Insight</option>
            </select>
            <input value={formData.importance} type="number" onChange={e => setFormData({ ...formData, importance: Number(e.target.value) })} min={0} max={1} step={0.1} style={{ width: 100, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} placeholder="Importance" />
            <input value={formData.confidence} type="number" onChange={e => setFormData({ ...formData, confidence: Number(e.target.value) })} min={0} max={1} step={0.1} style={{ width: 100, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} placeholder="Confidence" />
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input value={formData.tags} onChange={e => setFormData({ ...formData, tags: e.target.value })} placeholder="Tags (comma-separated)" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
            <input value={formData.workspace_id} onChange={e => setFormData({ ...formData, workspace_id: e.target.value })} placeholder="Workspace ID" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={storeMemory} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Storing...' : 'Store'}
            </button>
            <button onClick={() => setShowStore(false)} style={{ padding: '8px 16px', background: '#e5e7eb', color: '#374151', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Edit Form */}
      {showEdit && (
        <div style={{ background: '#fefce8', borderRadius: 12, padding: 16, marginBottom: 16, border: '1px solid #fde68a' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Edit Memory Entry</h3>
          <textarea value={editData.content} onChange={e => setEditData({ ...editData, content: e.target.value })} rows={3} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', resize: 'vertical', marginBottom: 8 }} />
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input value={editData.importance} type="number" onChange={e => setEditData({ ...editData, importance: Number(e.target.value) })} min={0} max={1} step={0.1} style={{ width: 100, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
            <input value={editData.confidence} type="number" onChange={e => setEditData({ ...editData, confidence: Number(e.target.value) })} min={0} max={1} step={0.1} style={{ width: 100, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
            <input value={editData.tags} onChange={e => setEditData({ ...editData, tags: e.target.value })} placeholder="Tags" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={updateMemory} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#f59e0b', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Updating...' : 'Update'}
            </button>
            <button onClick={() => setShowEdit(false)} style={{ padding: '8px 16px', background: '#e5e7eb', color: '#374151', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Memory Entries */}
      <div style={{ display: 'grid', gap: 8 }}>
        {entries.map(entry => (
          <div key={entry.entry_id}>
            <div onClick={() => selectEntry(entry.entry_id)} style={{ background: '#fff', borderRadius: 12, padding: 12, border: '1px solid #e2e8f0', cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ background: categoryColor(entry.category), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{entry.category}</span>
                {entry.pinned && <span style={{ fontSize: 11, color: '#7c3aed' }}>Pinned</span>}
                <span style={{ fontSize: 11, color: '#888' }}>v{entry.version}</span>
                <span style={{ fontSize: 11, color: '#888', marginLeft: 'auto' }}>{(entry.importance * 100).toFixed(0)}% · {entry.access_count} accesses</span>
              </div>
              <div style={{ fontSize: 13 }}>{entry.content}</div>
              {entry.tags.length > 0 && (
                <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                  {entry.tags.map(t => <span key={t} style={{ fontSize: 10, padding: '1px 6px', background: '#f3f4f6', borderRadius: 4 }}>{t}</span>)}
                </div>
              )}
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button onClick={(e) => { e.stopPropagation(); setEditData({ entry_id: entry.entry_id, content: entry.content, importance: entry.importance, confidence: entry.confidence, tags: entry.tags.join(', ') }); setShowEdit(true); }} style={{ padding: '2px 8px', background: '#eff6ff', color: '#2563eb', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                  Edit
                </button>
                {!entry.pinned && (
                  <button onClick={(e) => { e.stopPropagation(); pinMemory(entry.entry_id); }} style={{ padding: '2px 8px', background: '#faf5ff', color: '#7c3aed', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                    Pin
                  </button>
                )}
                <button onClick={(e) => { e.stopPropagation(); deleteMemory(entry.entry_id); }} style={{ padding: '2px 8px', background: '#fef2f2', color: '#ef4444', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                  Delete
                </button>
              </div>
            </div>

            {/* Expanded: Audit Trail + Lineage */}
            {selectedEntry === entry.entry_id && (
              <div style={{ marginLeft: 16, marginTop: 8, padding: 12, background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                {/* Audit Trail */}
                <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#6b7280' }}>Audit Trail ({auditTrail.length})</h4>
                <div style={{ display: 'grid', gap: 4, marginBottom: 12 }}>
                  {auditTrail.slice(-10).map(audit => (
                    <div key={audit.audit_id} style={{ display: 'flex', gap: 8, fontSize: 11, color: '#666' }}>
                      <span style={{ background: '#e5e7eb', padding: '1px 6px', borderRadius: 4 }}>{audit.stage}</span>
                      <span>{audit.trigger}</span>
                      <span style={{ marginLeft: 'auto' }}>{new Date(audit.timestamp * 1000).toLocaleTimeString()}</span>
                    </div>
                  ))}
                </div>

                {/* Version Lineage */}
                <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#6b7280' }}>Version Lineage ({lineage.length})</h4>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {lineage.map(ver => (
                    <div key={ver.entry_id} style={{ background: '#fff', borderRadius: 8, padding: 8, border: '1px solid #e2e8f0', fontSize: 11, maxWidth: 200 }}>
                      <div style={{ fontWeight: 500, marginBottom: 2 }}>v{ver.version}</div>
                      <div style={{ color: '#666' }}>{ver.content}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {entries.length === 0 && <div style={{ color: '#888', fontSize: 13, textAlign: 'center', padding: 24 }}>No memory entries yet. Store a memory to begin.</div>}
      </div>

      {/* Recent Audits */}
      {stats && stats.recent_audits.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginTop: 24, marginBottom: 12 }}>Recent Audit Activity</h3>
          <div style={{ display: 'grid', gap: 4 }}>
            {stats.recent_audits.slice(-5).map(audit => (
              <div key={audit.audit_id} style={{ display: 'flex', gap: 8, fontSize: 11, color: '#666', padding: '4px 8px', background: '#f9fafb', borderRadius: 6 }}>
                <span style={{ background: '#e5e7eb', padding: '1px 6px', borderRadius: 4 }}>{audit.stage}</span>
                <span style={{ fontFamily: 'monospace', fontSize: 10 }}>{audit.memory_id}</span>
                <span>{audit.trigger}</span>
                <span style={{ marginLeft: 'auto' }}>{new Date(audit.timestamp * 1000).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};