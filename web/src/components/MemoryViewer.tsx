import React, { useState, useEffect } from 'react';
import type { Agent, MemoryEntry, MemoryStats } from '../types';
import { api } from '../api/client';

interface MemoryViewerProps {
  agent: Agent;
}

export const MemoryViewer: React.FC<MemoryViewerProps> = ({ agent }) => {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [tags, setTags] = useState<Array<{ tag: string; count: number }>>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [editingMemory, setEditingMemory] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [newTag, setNewTag] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [agent.id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [memData, statsData, tagsData] = await Promise.all([
        api.memories.list(agent.id, undefined, 50),
        api.memories.stats(agent.id),
        api.memories.tags(agent.id),
      ]);
      setMemories(memData);
      setStats(statsData);
      setTags(tagsData);
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadData();
      return;
    }
    try {
      const results = await api.memories.search(agent.id, searchQuery);
      setMemories(results);
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const handleTagMemory = async (memoryId: string, tag: string) => {
    if (!tag.trim()) return;
    try {
      await api.memories.tag(agent.id, memoryId, [tag.trim()]);
      setNewTag('');
      loadData();
    } catch (err) {
      console.error('Tag failed:', err);
    }
  };

  const handleUntagMemory = async (memoryId: string, tag: string) => {
    try {
      await api.memories.untag(agent.id, memoryId, [tag]);
      loadData();
    } catch (err) {
      console.error('Untag failed:', err);
    }
  };

  const handleUpdateMemory = async (memoryId: string) => {
    try {
      await api.memories.update(agent.id, memoryId, { content: editContent });
      setEditingMemory(null);
      loadData();
    } catch (err) {
      console.error('Update failed:', err);
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!confirm('Delete this memory?')) return;
    try {
      await api.memories.delete(agent.id, memoryId);
      loadData();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleDecay = async () => {
    try {
      const result = await api.memories.decay(agent.id, 30, 0.1);
      alert(`Decayed ${result.decayed} memories`);
      loadData();
    } catch (err) {
      console.error('Decay failed:', err);
    }
  };

  const filteredMemories = selectedTag
    ? memories.filter((m) => m.tags?.includes(selectedTag))
    : memories;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-loading">Loading memories...</div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Memory System — {agent.name}</h2>
          {stats && (
            <span className="panel-subtitle">
              {stats.total_memories} memories · Avg importance: {stats.average_importance.toFixed(2)}
            </span>
          )}
        </div>
        <div className="panel-header-actions">
          <button className="btn-sm" onClick={handleDecay}>Decay Old</button>
          <button className="btn-sm" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {stats && (
        <div className="memory-stats-grid">
          <div className="memory-stat-card">
            <div className="memory-stat-value">{stats.total_memories}</div>
            <div className="memory-stat-label">Total</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{stats.layer_distribution.short_term || 0}</div>
            <div className="memory-stat-label">Short-term</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{stats.layer_distribution.long_term || 0}</div>
            <div className="memory-stat-label">Long-term</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{stats.layer_distribution.episodic || 0}</div>
            <div className="memory-stat-label">Episodic</div>
          </div>
        </div>
      )}

      <div className="panel-search-bar">
        <input
          type="text"
          className="panel-search-input"
          placeholder="Search memories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn-sm" onClick={handleSearch}>Search</button>
      </div>

      {tags.length > 0 && (
        <div className="memory-tags">
          <button
            className={`memory-tag ${!selectedTag ? 'active' : ''}`}
            onClick={() => setSelectedTag(null)}
          >
            All
          </button>
          {tags.map((t) => (
            <button
              key={t.tag}
              className={`memory-tag ${selectedTag === t.tag ? 'active' : ''}`}
              onClick={() => setSelectedTag(t.tag)}
            >
              {t.tag} ({t.count})
            </button>
          ))}
        </div>
      )}

      <div className="memory-list">
        {filteredMemories.map((mem) => (
          <div key={mem.id} className="memory-card">
            <div className="memory-card-header">
              <span className="memory-card-type">{mem.memory_type}</span>
              <div className="memory-importance">
                <div className="memory-importance-bar">
                  <div
                    className="memory-importance-fill"
                    style={{ width: `${mem.importance * 100}%` }}
                  />
                </div>
                <span>{(mem.importance * 100).toFixed(0)}%</span>
              </div>
            </div>

            {editingMemory === mem.id ? (
              <div className="memory-edit">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  rows={3}
                />
                <div className="memory-edit-actions">
                  <button className="btn-sm" onClick={() => handleUpdateMemory(mem.id)}>Save</button>
                  <button className="btn-sm" onClick={() => setEditingMemory(null)}>Cancel</button>
                </div>
              </div>
            ) : (
              <div className="memory-card-content">{mem.content}</div>
            )}

            {mem.tags && mem.tags.length > 0 && (
              <div className="memory-card-tags">
                {mem.tags.map((tag) => (
                  <span key={tag} className="memory-card-tag">
                    {tag}
                    <button
                      className="memory-tag-remove"
                      onClick={() => handleUntagMemory(mem.id, tag)}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}

            <div className="memory-card-footer">
              <div className="memory-tag-input">
                <input
                  type="text"
                  placeholder="Add tag..."
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleTagMemory(mem.id, newTag);
                      setNewTag('');
                    }
                  }}
                />
              </div>
              <div className="memory-card-actions">
                <button
                  className="btn-sm"
                  onClick={() => {
                    setEditingMemory(mem.id);
                    setEditContent(mem.content);
                  }}
                >
                  Edit
                </button>
                <button className="btn-sm btn-danger" onClick={() => handleDeleteMemory(mem.id)}>
                  Delete
                </button>
              </div>
            </div>
            <div className="memory-card-time">
              {new Date(mem.created_at).toLocaleString()}
            </div>
          </div>
        ))}

        {filteredMemories.length === 0 && (
          <div className="panel-empty">No memories found.</div>
        )}
      </div>
    </div>
  );
};