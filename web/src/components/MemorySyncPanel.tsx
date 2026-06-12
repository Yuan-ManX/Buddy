import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface MemorySyncStats {
  total_shared?: number;
  active_groups?: number;
  total_records?: number;
  config?: Record<string, unknown>;
}

interface SyncGroup {
  id: string;
  name: string;
  agent_ids: string[];
  sync_interval: number;
  last_sync: string | null;
  enabled: boolean;
  filters: Record<string, unknown>;
}

interface SharedRecord {
  id: string;
  source_agent_id: string;
  target_agent_id: string;
  content: string;
  memory_type: string;
  importance: number;
  tags: string[];
  shared_at: string;
  access_count: number;
}

export const MemorySyncPanel: React.FC = () => {
  const [stats, setStats] = useState<MemorySyncStats>({});
  const [groups, setGroups] = useState<SyncGroup[]>([]);
  const [records, setRecords] = useState<SharedRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'groups' | 'records' | 'share'>('overview');

  // Share form state
  const [shareForm, setShareForm] = useState({
    source_agent_id: '',
    target_agent_id: '',
    content: '',
    memory_type: 'event',
    importance: 0.5,
    tags: '',
  });

  // Group form state
  const [groupForm, setGroupForm] = useState({
    name: '',
    agent_ids: '',
    sync_interval: 600,
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{ similarity: number; content: string; id: string }>>([]);
  const [searchAgentIds, setSearchAgentIds] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, groupsRes, recordsRes] = await Promise.all([
        api.memorySync.stats().catch(() => ({})),
        api.memorySync.groups.list().catch(() => ({ groups: [] })),
        api.memorySync.records(undefined, undefined, 50).catch(() => ({ records: [], count: 0 })),
      ]);
      setStats(statsRes || {});
      setGroups((groupsRes as { groups: SyncGroup[] }).groups || []);
      setRecords((recordsRes as { records: SharedRecord[] }).records || []);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleShare = async () => {
    try {
      await api.memorySync.share({
        source_agent_id: shareForm.source_agent_id,
        target_agent_id: shareForm.target_agent_id,
        content: shareForm.content,
        memory_type: shareForm.memory_type,
        importance: shareForm.importance,
        tags: shareForm.tags ? shareForm.tags.split(',').map(t => t.trim()) : [],
      });
      setShareForm({ source_agent_id: '', target_agent_id: '', content: '', memory_type: 'event', importance: 0.5, tags: '' });
      loadData();
    } catch (err) {
      console.error('Share failed:', err);
    }
  };

  const handleBroadcast = async () => {
    try {
      await api.memorySync.broadcast({
        source_agent_id: shareForm.source_agent_id,
        content: shareForm.content,
        memory_type: shareForm.memory_type,
        importance: shareForm.importance,
        tags: shareForm.tags ? shareForm.tags.split(',').map(t => t.trim()) : [],
      });
      setShareForm({ source_agent_id: '', target_agent_id: '', content: '', memory_type: 'event', importance: 0.5, tags: '' });
      loadData();
    } catch (err) {
      console.error('Broadcast failed:', err);
    }
  };

  const handleCreateGroup = async () => {
    try {
      await api.memorySync.groups.create({
        name: groupForm.name,
        agent_ids: groupForm.agent_ids.split(',').map(s => s.trim()).filter(Boolean),
        sync_interval: groupForm.sync_interval,
      });
      setGroupForm({ name: '', agent_ids: '', sync_interval: 600 });
      loadData();
    } catch (err) {
      console.error('Create group failed:', err);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const agentIds = searchAgentIds
        ? searchAgentIds.split(',').map(s => s.trim()).filter(Boolean)
        : undefined;
      const res = await api.memorySync.search(searchQuery, agentIds, 10);
      setSearchResults(res.results || []);
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const handleToggleGroup = async (groupId: string, enabled: boolean) => {
    try {
      await api.memorySync.groups.update(groupId, { enabled });
      loadData();
    } catch (err) {
      console.error('Toggle group failed:', err);
    }
  };

  const handleDeleteGroup = async (groupId: string) => {
    try {
      await api.memorySync.groups.delete(groupId);
      loadData();
    } catch (err) {
      console.error('Delete group failed:', err);
    }
  };

  const handleSyncGroup = async (groupId: string) => {
    try {
      await api.memorySync.groups.sync(groupId);
      loadData();
    } catch (err) {
      console.error('Sync group failed:', err);
    }
  };

  if (loading) {
    return <div className="panel-loading">Loading Memory Sync...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header header-accent">
        <h2 className="panel-title">Memory Sync</h2>
        <div className="panel-tabs">
          {(['overview', 'groups', 'records', 'share'] as const).map(tab => (
            <button
              key={tab}
              className={`panel-tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="panel-grid">
          <div className="stat-card">
            <span className="stat-value">{stats.total_shared || 0}</span>
            <span className="stat-label">Shared Memories</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.active_groups || 0}</span>
            <span className="stat-label">Active Groups</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_records || 0}</span>
            <span className="stat-label">Sync Records</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{groups.filter(g => g.enabled).length}</span>
            <span className="stat-label">Enabled Groups</span>
          </div>

          {/* Cross-agent semantic search */}
          <div className="panel-card" style={{ gridColumn: 'span 2' }}>
            <h3>Cross-Agent Search</h3>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <input
                type="text"
                className="panel-input"
                placeholder="Search across agent memories..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ flex: 1 }}
              />
              <input
                type="text"
                className="panel-input"
                placeholder="Agent IDs (optional)"
                value={searchAgentIds}
                onChange={e => setSearchAgentIds(e.target.value)}
                style={{ width: '200px' }}
              />
              <button className="btn-primary" onClick={handleSearch}>Search</button>
            </div>
            {searchResults.length > 0 && (
              <div>
                {searchResults.map((r, i) => (
                  <div key={r.id || i} className="memory-card" style={{ marginBottom: '8px' }}>
                    <div className="memory-card-type">
                      Similarity: {(r.similarity * 100).toFixed(0)}%
                    </div>
                    <div className="memory-card-content">{r.content?.substring(0, 300)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Groups Tab */}
      {activeTab === 'groups' && (
        <div>
          <div className="panel-card" style={{ marginBottom: '16px' }}>
            <h3>Create Sync Group</h3>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input
                type="text"
                className="panel-input"
                placeholder="Group name"
                value={groupForm.name}
                onChange={e => setGroupForm({ ...groupForm, name: e.target.value })}
              />
              <input
                type="text"
                className="panel-input"
                placeholder="Agent IDs (comma-separated)"
                value={groupForm.agent_ids}
                onChange={e => setGroupForm({ ...groupForm, agent_ids: e.target.value })}
                style={{ flex: 1 }}
              />
              <input
                type="number"
                className="panel-input"
                placeholder="Sync interval (s)"
                value={groupForm.sync_interval}
                onChange={e => setGroupForm({ ...groupForm, sync_interval: Number(e.target.value) })}
                style={{ width: '140px' }}
              />
              <button className="btn-primary" onClick={handleCreateGroup}>Create</button>
            </div>
          </div>

          <div className="panel-list">
            {groups.map(group => (
              <div key={group.id} className="card-elevated" style={{ marginBottom: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>{group.name}</strong>
                    <span className={`agent-status-dot ${group.enabled ? 'active' : 'inactive'}`} style={{ marginLeft: '8px' }} />
                    <span style={{ color: 'var(--text-secondary)', fontSize: '13px', marginLeft: '8px' }}>
                      {group.agent_ids.length} agents | Interval: {group.sync_interval}s
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="btn-secondary"
                      onClick={() => handleSyncGroup(group.id)}
                      style={{ fontSize: '12px', padding: '4px 8px' }}
                    >
                      Sync Now
                    </button>
                    <button
                      className="btn-secondary"
                      onClick={() => handleToggleGroup(group.id, !group.enabled)}
                      style={{ fontSize: '12px', padding: '4px 8px' }}
                    >
                      {group.enabled ? 'Pause' : 'Resume'}
                    </button>
                    <button
                      className="btn-secondary"
                      onClick={() => handleDeleteGroup(group.id)}
                      style={{ fontSize: '12px', padding: '4px 8px', color: 'var(--red)' }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
                {group.last_sync && (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Last sync: {new Date(group.last_sync).toLocaleString()}
                  </div>
                )}
              </div>
            ))}
            {groups.length === 0 && (
              <div className="panel-empty">No sync groups configured.</div>
            )}
          </div>
        </div>
      )}

      {/* Records Tab */}
      {activeTab === 'records' && (
        <div className="panel-list">
          {records.map(record => (
            <div key={record.id} className="card-elevated" style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <div>
                  <span className="badge">{record.memory_type}</span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
                    {record.source_agent_id} → {record.target_agent_id}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Importance: {(record.importance * 100).toFixed(0)}% | Accesses: {record.access_count}
                </div>
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text)' }}>
                {record.content?.substring(0, 300)}
              </div>
              {record.tags && record.tags.length > 0 && (
                <div style={{ marginTop: '6px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  {record.tags.map((tag, i) => (
                    <span key={i} className="tag">{tag}</span>
                  ))}
                </div>
              )}
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Shared: {new Date(record.shared_at).toLocaleString()}
              </div>
            </div>
          ))}
          {records.length === 0 && (
            <div className="panel-empty">No shared memory records yet.</div>
          )}
        </div>
      )}

      {/* Share Tab */}
      {activeTab === 'share' && (
        <div>
          <div className="panel-card">
            <h3>Share Memory Between Agents</h3>
            <div className="form-group">
              <label>Source Agent ID</label>
              <input
                type="text"
                className="panel-input"
                placeholder="e.g., agent-strategy-001"
                value={shareForm.source_agent_id}
                onChange={e => setShareForm({ ...shareForm, source_agent_id: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Target Agent ID</label>
              <input
                type="text"
                className="panel-input"
                placeholder="e.g., agent-engineering-001"
                value={shareForm.target_agent_id}
                onChange={e => setShareForm({ ...shareForm, target_agent_id: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Memory Content</label>
              <textarea
                className="panel-input"
                placeholder="Memory content to share..."
                value={shareForm.content}
                onChange={e => setShareForm({ ...shareForm, content: e.target.value })}
                rows={4}
              />
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Type</label>
                <select
                  className="panel-input"
                  value={shareForm.memory_type}
                  onChange={e => setShareForm({ ...shareForm, memory_type: e.target.value })}
                >
                  <option value="event">Event</option>
                  <option value="fact">Fact</option>
                  <option value="preference">Preference</option>
                  <option value="skill">Skill</option>
                  <option value="decision">Decision</option>
                  <option value="observation">Observation</option>
                </select>
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Importance (0-1)</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={shareForm.importance}
                  onChange={e => setShareForm({ ...shareForm, importance: Number(e.target.value) })}
                  style={{ width: '100%' }}
                />
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{shareForm.importance}</span>
              </div>
              <div className="form-group" style={{ flex: 2 }}>
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  className="panel-input"
                  placeholder="e.g., important, project-alpha"
                  value={shareForm.tags}
                  onChange={e => setShareForm({ ...shareForm, tags: e.target.value })}
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              <button className="btn-primary" onClick={handleShare} disabled={!shareForm.source_agent_id || !shareForm.target_agent_id || !shareForm.content}>
                Share to Target
              </button>
              <button className="btn-secondary" onClick={handleBroadcast} disabled={!shareForm.source_agent_id || !shareForm.content}>
                Broadcast to All
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};