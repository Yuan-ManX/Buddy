import React, { useState, useEffect } from 'react';

interface KnowledgeStats {
  total_entries: number;
  total_verifications: number;
  total_topics: number;
  total_subscriptions: number;
  active_contributors: number;
  entries_by_type: Record<string, number>;
  entries_by_status: Record<string, number>;
  entries_by_verification: Record<string, number>;
  top_contributors: { agent_id: string; contributions: number }[];
  topics: { topic_id: string; name: string; entry_count: number; subscriber_count: number }[];
}

interface KnowledgeEntry {
  entry_id: string;
  knowledge_type: string;
  topic: string;
  content: string;
  source_agent_name: string;
  confidence: number;
  status: string;
  verification_level: string;
  created_at: number;
}

export const KnowledgeNetworkPanel: React.FC = () => {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [showPublish, setShowPublish] = useState(false);
  const [showTopic, setShowTopic] = useState(false);
  const [formData, setFormData] = useState({
    knowledge_type: 'fact', topic: 'general', content: '', source_agent_id: 'buddy-coder',
    source_agent_name: 'Buddy Coder', confidence: 0.8, tags: '',
  });
  const [topicForm, setTopicForm] = useState({ name: '', description: '' });
  const [queryTopic, setQueryTopic] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchEntries();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/knowledge-network/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch knowledge stats:', e); }
  };

  const fetchEntries = async () => {
    try {
      const url = queryTopic ? `/api/knowledge-network/query?topic=${queryTopic}&limit=30` : '/api/knowledge-network/query?limit=30';
      const res = await fetch(url);
      const data = await res.json();
      setEntries(data.entries || []);
    } catch (e) { console.error('Failed to fetch entries:', e); }
  };

  const publishEntry = async () => {
    setLoading(true);
    try {
      await fetch('/api/knowledge-network/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowPublish(false);
      setFormData({ ...formData, content: '', tags: '' });
      fetchStats();
      fetchEntries();
    } catch (e) { console.error('Publish failed:', e); }
    setLoading(false);
  };

  const createTopic = async () => {
    setLoading(true);
    try {
      await fetch('/api/knowledge-network/topic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(topicForm),
      });
      setShowTopic(false);
      setTopicForm({ name: '', description: '' });
      fetchStats();
    } catch (e) { console.error('Create topic failed:', e); }
    setLoading(false);
  };

  const verifyEntry = async (entryId: string) => {
    await fetch('/api/knowledge-network/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entry_id: entryId,
        verifying_agent_id: 'buddy-reviewer',
        verifying_agent_name: 'Buddy Reviewer',
        agreement: true,
        confidence: 0.9,
        comment: 'Verified by peer review.',
      }),
    });
    fetchStats();
    fetchEntries();
  };

  const typeColor = (type: string) => {
    const map: Record<string, string> = {
      fact: '#3b82f6', insight: '#8b5cf6', pattern: '#ec4899', strategy: '#f59e0b',
      warning: '#ef4444', discovery: '#16a34a', best_practice: '#06b6d4',
    };
    return map[type] || '#6b7280';
  };

  const statusColor = (status: string) => {
    const map: Record<string, string> = {
      accepted: '#16a34a', verified: '#3b82f6', proposed: '#f59e0b',
      disputed: '#ef4444', deprecated: '#6b7280', superseded: '#8b5cf6',
    };
    return map[status] || '#6b7280';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Knowledge Network</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Cross-agent knowledge sharing with verification and collaborative learning</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setShowTopic(true)} style={{ padding: '8px 16px', background: '#6b7280', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            + Topic
          </button>
          <button onClick={() => setShowPublish(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            + Publish Entry
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_entries}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Entries</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_verifications}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Verifications</div>
          </div>
          <div style={{ flex: 1, background: '#fef3c7', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#d97706' }}>{stats.total_topics}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Topics</div>
          </div>
          <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.active_contributors}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Contributors</div>
          </div>
        </div>
      )}

      {/* Type Distribution */}
      {stats?.entries_by_type && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {Object.entries(stats.entries_by_type).map(([type, count]) => (
            <span key={type} style={{ background: typeColor(type), color: '#fff', padding: '4px 12px', borderRadius: 8, fontSize: 12 }}>
              {type.replace(/_/g, ' ')}: {count}
            </span>
          ))}
        </div>
      )}

      {/* Search */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          value={queryTopic}
          onChange={e => setQueryTopic(e.target.value)}
          placeholder="Filter by topic..."
          style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
        />
        <button onClick={fetchEntries} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Search</button>
      </div>

      {/* Entries */}
      <div style={{ display: 'grid', gap: 8 }}>
        {entries.map(entry => (
          <div key={entry.entry_id} style={{ background: '#fff', borderRadius: 12, padding: 12, border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ background: typeColor(entry.knowledge_type), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{entry.knowledge_type}</span>
              <span style={{ background: statusColor(entry.status), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{entry.status}</span>
              <span style={{ fontSize: 11, color: '#888' }}>{entry.verification_level.replace(/_/g, ' ')}</span>
              <span style={{ fontSize: 11, color: '#888', marginLeft: 'auto' }}>{(entry.confidence * 100).toFixed(0)}%</span>
            </div>
            <div style={{ fontSize: 13, marginBottom: 4 }}>{entry.content}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: '#888' }}>
              <span>{entry.source_agent_name} · {entry.topic}</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <span>{new Date(entry.created_at * 1000).toLocaleString()}</span>
                <button onClick={() => verifyEntry(entry.entry_id)} style={{ padding: '2px 8px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 4, cursor: 'pointer', fontSize: 11, color: '#16a34a' }}>
                  Verify
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Publish Modal */}
      {showPublish && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 500, maxHeight: '80vh', overflow: 'auto' }}>
            <h3 style={{ marginBottom: 16 }}>Publish Knowledge Entry</h3>
            <div style={{ display: 'grid', gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Type</label>
                <select value={formData.knowledge_type} onChange={e => setFormData({ ...formData, knowledge_type: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }}>
                  {['fact', 'insight', 'pattern', 'strategy', 'warning', 'discovery', 'best_practice'].map(t => (
                    <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Topic</label><input value={formData.topic} onChange={e => setFormData({ ...formData, topic: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Content</label><textarea value={formData.content} onChange={e => setFormData({ ...formData, content: e.target.value })} rows={3} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', resize: 'vertical' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Confidence (0-1)</label><input type="range" min="0" max="1" step="0.1" value={formData.confidence} onChange={e => setFormData({ ...formData, confidence: parseFloat(e.target.value) })} style={{ width: '100%' }} /><span style={{ fontSize: 12 }}>{formData.confidence}</span></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Tags (comma-separated)</label><input value={formData.tags} onChange={e => setFormData({ ...formData, tags: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button onClick={() => setShowPublish(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={publishEntry} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Publish</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Topic Modal */}
      {showTopic && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 400 }}>
            <h3 style={{ marginBottom: 16 }}>Create Knowledge Topic</h3>
            <div style={{ display: 'grid', gap: 10 }}>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Name</label><input value={topicForm.name} onChange={e => setTopicForm({ ...topicForm, name: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Description</label><textarea value={topicForm.description} onChange={e => setTopicForm({ ...topicForm, description: e.target.value })} rows={2} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', resize: 'vertical' }} /></div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button onClick={() => setShowTopic(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={createTopic} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};