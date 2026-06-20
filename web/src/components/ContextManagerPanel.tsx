import React, { useState, useEffect } from 'react';

interface ContextItem {
  item_id: string;
  context_type: string;
  priority: string;
  token_count: number;
  relevance: number;
}

interface SnapshotInfo {
  snapshot_id: string;
  label: string;
  total_tokens: number;
  item_count: number;
  created_at: number;
}

export const ContextManagerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [items, setItems] = useState<ContextItem[]>([]);
  const [snapshots, setSnapshots] = useState<SnapshotInfo[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [showSnapshot, setShowSnapshot] = useState(false);
  const [formData, setFormData] = useState({
    content: '',
    context_type: 'user_message',
    priority: 'medium',
    pin: false,
  });
  const [snapshotForm, setSnapshotForm] = useState({ agent_id: '', label: '' });
  const [summarizeId, setSummarizeId] = useState('');
  const [summarizeText, setSummarizeText] = useState('');
  const [queryFilter, setQueryFilter] = useState({ context_type: '', priority: '', limit: '50' });
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); fetchItems(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/context-manager/stats');
      const data = await res.json();
      setStats(data);
      if (data.snapshots) setSnapshots(data.snapshots);
    } catch (e) { console.error('Fetch stats failed:', e); }
  };

  const fetchItems = async () => {
    try {
      const params = new URLSearchParams();
      if (queryFilter.context_type) params.set('context_type', queryFilter.context_type);
      if (queryFilter.priority) params.set('priority', queryFilter.priority);
      params.set('limit', queryFilter.limit);
      const res = await fetch(`/api/context-manager/query?${params.toString()}`);
      const data = await res.json();
      setItems(data.items || []);
    } catch (e) { console.error('Fetch items failed:', e); }
  };

  const addContextItem = async () => {
    setLoading(true);
    try {
      await fetch('/api/context-manager/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      setShowAdd(false);
      setFormData({ content: '', context_type: 'user_message', priority: 'medium', pin: false });
      fetchStats();
      fetchItems();
    } catch (e) { console.error('Add item failed:', e); }
    setLoading(false);
  };

  const summarizeItem = async () => {
    setLoading(true);
    try {
      await fetch('/api/context-manager/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: summarizeId, summary: summarizeText }),
      });
      setSummarizeId('');
      setSummarizeText('');
      fetchStats();
      fetchItems();
    } catch (e) { console.error('Summarize failed:', e); }
    setLoading(false);
  };

  const createSnapshot = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/context-manager/snapshot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(snapshotForm),
      });
      const data = await res.json();
      setShowSnapshot(false);
      alert(`Snapshot created: ${data.snapshot_id}`);
      fetchStats();
    } catch (e) { console.error('Snapshot failed:', e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Context Manager</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Intelligent context window optimization with priority-based content retention and summarization</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setShowSnapshot(true)}
            style={{ padding: '8px 16px', background: '#6b7280', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            Snapshot
          </button>
          <button
            onClick={() => setShowAdd(true)}
            style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            + Add Item
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Total Items', value: stats.total_items ?? 0, color: '#2563eb' },
            { label: 'Window Tokens', value: stats.window_tokens ?? stats.total_tokens ?? 0, color: '#7c3aed' },
            { label: 'Max Window', value: stats.max_window_tokens ?? 8192, color: '#059669' },
            { label: 'Snapshots', value: snapshots.length, color: '#d97706' },
          ].map((s) => (
            <div key={s.label} style={{ background: '#fff', borderRadius: 12, padding: 16, border: `1px solid ${s.color}20`, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 12, color: '#666' }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Add Item Modal */}
      {showAdd && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 16, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Add Context Item</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <textarea
              value={formData.content}
              onChange={e => setFormData({ ...formData, content: e.target.value })}
              placeholder="Content text..."
              rows={4}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13, resize: 'vertical' }}
            />
            <select
              value={formData.context_type}
              onChange={e => setFormData({ ...formData, context_type: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="user_message">User Message</option>
              <option value="assistant_response">Assistant Response</option>
              <option value="system_message">System Message</option>
              <option value="tool_call">Tool Call</option>
              <option value="tool_result">Tool Result</option>
              <option value="memory">Memory</option>
              <option value="skill">Skill</option>
            </select>
            <select
              value={formData.priority}
              onChange={e => setFormData({ ...formData, priority: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
              <input type="checkbox" checked={formData.pin} onChange={e => setFormData({ ...formData, pin: e.target.checked })} />
              Pin item (never evict)
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowAdd(false)} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={addContextItem} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
                {loading ? 'Adding...' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Snapshot Modal */}
      {showSnapshot && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 16, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Create Snapshot</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input
              value={snapshotForm.agent_id}
              onChange={e => setSnapshotForm({ ...snapshotForm, agent_id: e.target.value })}
              placeholder="Agent ID"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <input
              value={snapshotForm.label}
              onChange={e => setSnapshotForm({ ...snapshotForm, label: e.target.value })}
              placeholder="Snapshot label"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowSnapshot(false)} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={createSnapshot} disabled={loading} style={{ padding: '8px 16px', background: '#6b7280', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
                {loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summarize Section */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Summarize Item</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={summarizeId}
            onChange={e => setSummarizeId(e.target.value)}
            placeholder="Item ID"
            style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          />
          <input
            value={summarizeText}
            onChange={e => setSummarizeText(e.target.value)}
            placeholder="Summary text"
            style={{ flex: 2, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          />
          <button
            onClick={summarizeItem}
            disabled={loading}
            style={{ padding: '8px 16px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', whiteSpace: 'nowrap' }}
          >
            Summarize
          </button>
        </div>
      </div>

      {/* Query Filters */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Query Context</h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            value={queryFilter.context_type}
            onChange={e => setQueryFilter({ ...queryFilter, context_type: e.target.value })}
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          >
            <option value="">All Types</option>
            <option value="user_message">User Message</option>
            <option value="assistant_response">Assistant Response</option>
            <option value="system_message">System Message</option>
            <option value="tool_call">Tool Call</option>
            <option value="tool_result">Tool Result</option>
            <option value="memory">Memory</option>
            <option value="skill">Skill</option>
          </select>
          <select
            value={queryFilter.priority}
            onChange={e => setQueryFilter({ ...queryFilter, priority: e.target.value })}
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          >
            <option value="">All Priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <input
            value={queryFilter.limit}
            onChange={e => setQueryFilter({ ...queryFilter, limit: e.target.value })}
            placeholder="Limit"
            type="number"
            style={{ width: 80, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
          />
          <button
            onClick={fetchItems}
            style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            Query
          </button>
        </div>
      </div>

      {/* Context Items List */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
          Context Items ({items.length})
        </h3>
        {items.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: 13 }}>No context items found. Add some items to get started.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {items.map((item) => (
              <div key={item.item_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fafafa' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 12, fontFamily: 'monospace', color: '#2563eb' }}>{item.item_id}</div>
                  <div style={{ fontSize: 11, color: '#9ca3af' }}>
                    Type: {item.context_type} | Priority: {item.priority} | Tokens: {item.token_count} | Relevance: {item.relevance}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 10,
                    fontWeight: 600,
                    background: item.priority === 'critical' ? '#fef2f2' : item.priority === 'high' ? '#fef3c7' : item.priority === 'medium' ? '#dbeafe' : '#f3f4f6',
                    color: item.priority === 'critical' ? '#dc2626' : item.priority === 'high' ? '#d97706' : item.priority === 'medium' ? '#2563eb' : '#6b7280',
                  }}>
                    {item.priority}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Snapshots */}
      {snapshots.length > 0 && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginTop: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Snapshots ({snapshots.length})</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {snapshots.map((s) => (
              <div key={s.snapshot_id} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fafafa' }}>
                <div style={{ fontWeight: 600, fontSize: 12 }}>{s.label || s.snapshot_id}</div>
                <div style={{ fontSize: 11, color: '#9ca3af' }}>Tokens: {s.total_tokens} | Items: {s.item_count}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};