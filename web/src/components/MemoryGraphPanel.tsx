import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#4f46e5',
  secondary: '#818cf8',
  bg: '#eef2ff',
  border: '#a5b4fc',
  accent: '#e0e7ff',
  text: '#3730a3',
};

const NODE_CATEGORIES = [
  'fact', 'concept', 'event', 'person', 'place',
  'procedure', 'opinion', 'goal', 'decision', 'learning',
];

const RETRIEVAL_STRATEGIES = [
  'direct', 'breadth_first', 'depth_first', 'semantic', 'multi_hop', 'subgraph',
];

export const MemoryGraphPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'add-node' | 'retrieve'>('overview');

  const [nodeForm, setNodeForm] = useState({
    content: '', category: 'fact', importance: 0.5, confidence: 0.5, tags: '',
  });
  const [adding, setAdding] = useState(false);

  const [retrieveForm, setRetrieveForm] = useState({
    query: '', strategy: 'semantic', limit: '20',
  });
  const [retrieving, setRetrieving] = useState(false);
  const [retrieveResults, setRetrieveResults] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.memoryGraph.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load memory graph data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAddNode = async () => {
    if (!nodeForm.content.trim()) return;
    try {
      setAdding(true);
      const result = await api.memoryGraph.addNode({
        content: nodeForm.content,
        category: nodeForm.category,
        importance: nodeForm.importance,
        confidence: nodeForm.confidence,
        tags: nodeForm.tags ? nodeForm.tags.split(',').map(s => s.trim()) : undefined,
      });
      toast.success(`Node added: ${result.node_id}`);
      setNodeForm({ content: '', category: 'fact', importance: 0.5, confidence: 0.5, tags: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
    finally { setAdding(false); }
  };

  const handleRetrieve = async () => {
    try {
      setRetrieving(true);
      const result = await api.memoryGraph.retrieve({
        query: retrieveForm.query || undefined,
        strategy: retrieveForm.strategy,
        limit: parseInt(retrieveForm.limit) || 20,
      });
      setRetrieveResults(result);
      const nodeCount = result.nodes?.length ?? 0;
      toast.success(`Retrieved ${nodeCount} nodes`);
    } catch (e: any) { toast.error(e.message); }
    finally { setRetrieving(false); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🕸️ Contextual Memory Graph</h2>
          <p className="panel-subtitle">Graph-based semantic memory with rich connections</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading memory graph...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🕸️ Contextual Memory Graph</h2>
        <p className="panel-subtitle">Graph-based semantic memory with rich connections</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_nodes ?? '-'}</span><span className="stat-label">Total Nodes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_edges ?? '-'}</span><span className="stat-label">Total Edges</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_retrievals ?? '-'}</span><span className="stat-label">Retrievals</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.graph_density?.toFixed?.(4) ?? '-'}</span><span className="stat-label">Graph Density</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'add-node', 'retrieve'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s === 'add-node' ? 'Add Node' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Memory Graph Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Importance</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_importance?.toFixed?.(2) ?? '-'}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Confidence</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_confidence?.toFixed?.(2) ?? '-'}</div>
              </div>
            </div>
          </div>
          {stats.categories && Object.keys(stats.categories).length > 0 && (
            <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8, marginBottom: 12 }}>
              <h4 style={{ color: themeColors.text }}>Categories</h4>
              {Object.entries(stats.categories).map(([cat, count]: [string, any]) => (
                <div key={cat} className="dashboard-stat-row">
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{cat}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
          {stats.edge_types && Object.keys(stats.edge_types).length > 0 && (
            <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8 }}>
              <h4 style={{ color: themeColors.text }}>Edge Types</h4>
              {Object.entries(stats.edge_types).map(([etype, count]: [string, any]) => (
                <div key={etype} className="dashboard-stat-row">
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{etype.replace(/_/g, ' ')}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Node */}
      {activeSection === 'add-node' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Add Memory Node</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={3}
                value={nodeForm.content}
                onChange={e => setNodeForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the memory content..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Category</label>
                <select value={nodeForm.category} onChange={e => setNodeForm(f => ({ ...f, category: e.target.value }))}>
                  {NODE_CATEGORIES.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Importance ({nodeForm.importance.toFixed(1)})</label>
                <input type="range" min="0" max="1" step="0.1" value={nodeForm.importance}
                  onChange={e => setNodeForm(f => ({ ...f, importance: parseFloat(e.target.value) }))} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Confidence ({nodeForm.confidence.toFixed(1)})</label>
                <input type="range" min="0" max="1" step="0.1" value={nodeForm.confidence}
                  onChange={e => setNodeForm(f => ({ ...f, confidence: parseFloat(e.target.value) }))} />
              </div>
              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={nodeForm.tags}
                  onChange={e => setNodeForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="memory, important, graph"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddNode}
              disabled={adding || !nodeForm.content.trim()}
            >
              {adding ? 'Adding...' : '🕸️ Add Node'}
            </button>
          </div>
        </div>
      )}

      {/* Retrieve */}
      {activeSection === 'retrieve' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Retrieve from Memory Graph</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Search Query</label>
              <input
                type="text"
                value={retrieveForm.query}
                onChange={e => setRetrieveForm(f => ({ ...f, query: e.target.value }))}
                placeholder="Search memory graph..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Strategy</label>
                <select value={retrieveForm.strategy} onChange={e => setRetrieveForm(f => ({ ...f, strategy: e.target.value }))}>
                  {RETRIEVAL_STRATEGIES.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Limit</label>
                <input type="number" value={retrieveForm.limit} onChange={e => setRetrieveForm(f => ({ ...f, limit: e.target.value }))}
                  min="1" max="100" />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRetrieve}
              disabled={retrieving}
            >
              {retrieving ? 'Retrieving...' : '🔍 Retrieve'}
            </button>
          </div>

          {retrieveResults && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ color: themeColors.text }}>
                Results ({retrieveResults.nodes?.length ?? 0} nodes, {retrieveResults.total_matches ?? 0} matches)
              </h4>
              {(!retrieveResults.nodes || retrieveResults.nodes.length === 0) ? (
                <div className="panel-empty">No nodes found matching your query</div>
              ) : (
                <div className="forge-skill-list">
                  {retrieveResults.nodes.map((n: any, idx: number) => (
                    <div key={n.node_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ color: themeColors.text }}>{n.content?.slice(0, 120)}</div>
                        <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                          {n.category}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Importance: {n.importance?.toFixed?.(2) ?? '0.00'} | Confidence: {n.confidence?.toFixed?.(2) ?? '0.00'} | Accesses: {n.access_count ?? 0}</div>
                        {n.tags?.length > 0 && (
                          <div style={{ marginTop: 4 }}>
                            {n.tags.map((tag: string) => (
                              <span key={tag} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {retrieveResults.edges?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ color: themeColors.text }}>Edges ({retrieveResults.edges.length})</h4>
                  <div className="forge-skill-list">
                    {retrieveResults.edges.map((e: any, idx: number) => (
                      <div key={e.edge_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.secondary}` }}>
                        <div className="forge-skill-meta">
                          <div>{e.source_id} → {e.target_id} ({e.edge_type?.replace(/_/g, ' ')})</div>
                          <div>Weight: {e.weight?.toFixed?.(2) ?? '-'}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MemoryGraphPanel;