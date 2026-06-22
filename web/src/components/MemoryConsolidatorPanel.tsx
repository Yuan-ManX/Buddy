import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { MemoryConsolidatorStats, MemoryEntryItem, ConsolidatedMemory, ConceptNode } from '../types';

export const MemoryConsolidatorPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<MemoryConsolidatorStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'store' | 'search' | 'consolidate' | 'concept-map'>('overview');

  // Store form
  const [storeForm, setStoreForm] = useState({
    content: '', memory_type: 'episodic', importance: '5', tags: '', source_session: '',
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('');
  const [searchResults, setSearchResults] = useState<MemoryEntryItem[]>([]);

  // Consolidate state
  const [consolidateStrategy, setConsolidateStrategy] = useState('');
  const [consolidateResult, setConsolidateResult] = useState<ConsolidatedMemory[]>([]);

  // Concept map state
  const [conceptMap, setConceptMap] = useState<ConceptNode[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.memoryConsolidator.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load memory consolidator data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleStore = async () => {
    if (!storeForm.content.trim()) return;
    try {
      await api.memoryConsolidator.store({
        content: storeForm.content,
        memory_type: storeForm.memory_type,
        importance: parseInt(storeForm.importance) || 5,
        tags: storeForm.tags ? storeForm.tags.split(',').map(s => s.trim()) : undefined,
        source_session: storeForm.source_session || undefined,
      });
      toast.success('Memory stored successfully');
      setStoreForm({ content: '', memory_type: 'episodic', importance: '5', tags: '', source_session: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const result = await api.memoryConsolidator.search({
        query: searchQuery,
        memory_type: searchType || undefined,
        limit: 20,
      });
      setSearchResults(result.results);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleConsolidate = async () => {
    try {
      const result = await api.memoryConsolidator.consolidate({
        strategy: consolidateStrategy || undefined,
      });
      setConsolidateResult(result.consolidated);
      toast.success(`Consolidated ${result.consolidated.length} memories`);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadConceptMap = async () => {
    try {
      const result = await api.memoryConsolidator.conceptMap();
      setConceptMap(result.concepts);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDecay = async () => {
    try {
      const result = await api.memoryConsolidator.decay({});
      toast.success(`Decayed ${result.removed} memory entries`);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const memoryTypeColors: Record<string, string> = {
    episodic: '#4f6ef7',
    semantic: '#22c55e',
    procedural: '#8b5cf6',
  };

  const memoryTypeLabels: Record<string, string> = {
    episodic: 'Episodic',
    semantic: 'Semantic',
    procedural: 'Procedural',
  };

  const importanceColor = (imp: number) => {
    if (imp >= 8) return '#ef4444';
    if (imp >= 5) return '#f59e0b';
    return '#22c55e';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Memory Consolidator</h2>
          <p className="panel-subtitle">Unified memory management across episodic, semantic, and procedural layers</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading memory consolidator data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Memory Consolidator</h2>
        <p className="panel-subtitle">Store, search, consolidate, and manage memory across multiple layers</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.episodic_count}</span><span className="stat-label">Episodic</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.semantic_count}</span><span className="stat-label">Semantic</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.procedural_count}</span><span className="stat-label">Procedural</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_consolidations}</span><span className="stat-label">Consolidations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.memory_usage.toLocaleString()}</span><span className="stat-label">Memory Usage</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'store', 'search', 'consolidate', 'concept-map'] as const).map(s => (
          <button key={s} className={`forge-tab ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>
            {s === 'concept-map' ? 'Concept Map' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Memory Distribution</h3>
          <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
            {[
              { label: 'Episodic', count: stats.episodic_count, color: '#4f6ef7', bg: '#e8eaf6' },
              { label: 'Semantic', count: stats.semantic_count, color: '#22c55e', bg: '#e8f5e9' },
              { label: 'Procedural', count: stats.procedural_count, color: '#8b5cf6', bg: '#f3e5f5' },
            ].map(item => (
              <div key={item.label} style={{
                flex: 1,
                padding: 20,
                background: item.bg,
                borderRadius: 8,
                textAlign: 'center',
                border: `2px solid ${item.color}`,
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 700, color: item.color }}>{item.count}</div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: 4 }}>{item.label}</div>
              </div>
            ))}
          </div>

          <div className="dashboard-stat-row"><span>Total Consolidations</span><strong>{stats.total_consolidations}</strong></div>
          <div className="dashboard-stat-row"><span>Memory Usage</span><strong>{stats.memory_usage.toLocaleString()}</strong></div>

          <h3 style={{ marginTop: 20 }}>By Strategy</h3>
          {Object.entries(stats.by_strategy).length > 0 ? (
            Object.entries(stats.by_strategy).map(([strategy, count]) => (
              <div key={strategy} className="dashboard-stat-row">
                <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{strategy.replace(/_/g, ' ')}</span>
                <strong>{count}</strong>
              </div>
            ))
          ) : (
            <div className="panel-empty">No consolidation data yet</div>
          )}

          <div style={{ marginTop: 20, display: 'flex', gap: 8 }}>
            <button className="btn-sm" style={{ background: '#ef4444', color: '#fff', border: 'none' }} onClick={handleDecay}>
              Run Memory Decay
            </button>
          </div>
        </div>
      )}

      {/* Store */}
      {activeSection === 'store' && (
        <div className="dashboard-section">
          <h3>Store New Memory</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={4}
                value={storeForm.content}
                onChange={e => setStoreForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the memory content to store..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Memory Type</label>
                <select value={storeForm.memory_type} onChange={e => setStoreForm(f => ({ ...f, memory_type: e.target.value }))}>
                  {['episodic', 'semantic', 'procedural'].map(t => (
                    <option key={t} value={t}>{memoryTypeLabels[t]}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Importance (1-10)</label>
                <select value={storeForm.importance} onChange={e => setStoreForm(f => ({ ...f, importance: e.target.value }))}>
                  {Array.from({ length: 10 }, (_, i) => (
                    <option key={i + 1} value={String(i + 1)}>{i + 1}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={storeForm.tags}
                  onChange={e => setStoreForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="important, meeting, project-x"
                />
              </div>
              <div className="form-group">
                <label>Source Session</label>
                <input
                  type="text"
                  value={storeForm.source_session}
                  onChange={e => setStoreForm(f => ({ ...f, source_session: e.target.value }))}
                  placeholder="session-id"
                />
              </div>
            </div>
            <button className="btn-primary" onClick={handleStore}>Store Memory</button>
          </div>
        </div>
      )}

      {/* Search */}
      {activeSection === 'search' && (
        <div className="dashboard-section">
          <h3>Search Memories</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label>Search Query</label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Enter search query..."
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                />
              </div>
              <div className="form-group">
                <label>Memory Type</label>
                <select value={searchType} onChange={e => setSearchType(e.target.value)}>
                  <option value="">All Types</option>
                  {['episodic', 'semantic', 'procedural'].map(t => (
                    <option key={t} value={t}>{memoryTypeLabels[t]}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ alignSelf: 'flex-end' }}>
                <button className="btn-primary" onClick={handleSearch}>Search</button>
              </div>
            </div>
          </div>

          {searchResults.length === 0 ? (
            <div className="panel-empty">Enter a search query above to find memories.</div>
          ) : (
            <div className="forge-skill-list">
              {searchResults.map((entry: MemoryEntryItem) => (
                <div key={entry.entry_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.9rem' }}>{entry.content}</div>
                    <span className="dashboard-badge" style={{ background: memoryTypeColors[entry.memory_type] || '#666', color: '#fff' }}>
                      {memoryTypeLabels[entry.memory_type] || entry.memory_type}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      <span style={{ color: importanceColor(entry.importance), fontWeight: 700 }}>
                        Importance: {entry.importance}/10
                      </span>
                      {' | '}
                      <span>Accesses: {entry.access_count}</span>
                    </div>
                    {entry.tags.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        {entry.tags.map(tag => (
                          <span key={tag} style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            margin: '2px',
                            background: '#e8eaf6',
                            color: '#4f6ef7',
                            borderRadius: 12,
                            fontSize: '0.75rem',
                          }}>{tag}</span>
                        ))}
                      </div>
                    )}
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 4 }}>
                      Created: {new Date(entry.created_at).toLocaleString()}
                      {entry.last_accessed && ` | Last Accessed: ${new Date(entry.last_accessed).toLocaleString()}`}
                    </div>
                    {entry.source_session && (
                      <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>Session: {entry.source_session}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Consolidate */}
      {activeSection === 'consolidate' && (
        <div className="dashboard-section">
          <h3>Trigger Consolidation</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Strategy (optional)</label>
              <select value={consolidateStrategy} onChange={e => setConsolidateStrategy(e.target.value)}>
                <option value="">Default</option>
                {['summarize', 'merge_similar', 'extract_patterns', 'build_knowledge_graph', 'prune_low_importance'].map(s => (
                  <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <button className="btn-primary" onClick={handleConsolidate}>Run Consolidation</button>
          </div>

          {consolidateResult.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4>Consolidation Results ({consolidateResult.length})</h4>
              <div className="forge-skill-list">
                {consolidateResult.map((item: ConsolidatedMemory) => (
                  <div key={item.consolidated_id} className="forge-skill-card">
                    <div className="forge-skill-header">
                      <div className="forge-skill-name">{item.summary}</div>
                      <span className="dashboard-badge active">{item.strategy}</span>
                    </div>
                    <div className="forge-skill-meta">
                      <div>Source Entries: {item.entry_count} | Quality: {(item.quality_score * 100).toFixed(0)}%</div>
                      <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 4, height: 6 }}>
                        <div style={{
                          width: `${(item.quality_score * 100)}%`,
                          background: `linear-gradient(90deg, #ef4444, #f59e0b, #22c55e)`,
                          height: '100%',
                          borderRadius: 4,
                        }} />
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 4 }}>
                        {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Concept Map */}
      {activeSection === 'concept-map' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3>Concept Map</h3>
            <button className="btn-primary-sm" onClick={handleLoadConceptMap}>Load Concept Map</button>
          </div>

          {conceptMap.length === 0 ? (
            <div className="panel-empty">Click "Load Concept Map" to view concept relationships.</div>
          ) : (
            <div className="forge-skill-list">
              {conceptMap.map((concept: ConceptNode) => (
                <div key={concept.concept} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{concept.concept}</div>
                    <span className="dashboard-badge" style={{ background: '#4f6ef7', color: '#fff' }}>
                      Weight: {concept.weight.toFixed(2)}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Entries: {concept.entry_count}</div>
                    {concept.connections.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ fontWeight: 600, marginBottom: 4, fontSize: '0.85rem', color: '#374151' }}>Connections:</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {concept.connections.map((conn, idx) => (
                            <span key={idx} style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '4px 10px',
                              background: `rgba(79, 110, 247, ${Math.min(0.3, conn.strength * 0.5)})`,
                              borderRadius: 16,
                              fontSize: '0.8rem',
                              border: `1px solid rgba(79, 110, 247, ${Math.min(0.5, conn.strength)})`,
                            }}>
                              {conn.concept}
                              <span style={{
                                marginLeft: 6,
                                fontSize: '0.7rem',
                                color: '#4f6ef7',
                                fontWeight: 600,
                              }}>
                                {(conn.strength * 100).toFixed(0)}%
                              </span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MemoryConsolidatorPanel;