import React, { useState, useEffect, useCallback } from 'react';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

interface KnowledgeFabricStats {
  total_nodes: number;
  total_edges: number;
  total_clusters: number;
  total_queries: number;
  nodes_by_domain: Record<string, number>;
  nodes_by_type: Record<string, number>;
  total_tags: number;
  avg_confidence: number;
}

interface KnowledgeNode {
  node_id: string;
  title: string;
  summary: string;
  domain: string;
  knowledge_type: string;
  confidence: number;
  tags: string[];
}

interface QueryResult {
  query_id: string;
  total_matches: number;
  query_time_ms: number;
  nodes: KnowledgeNode[];
  suggested_related: string[];
}

interface SynthesisResult {
  summary: string;
  sources: Array<{ node_id: string; title: string; domain: string; confidence: number }>;
  total_sources_found: number;
  query_time_ms: number;
}

export const KnowledgeFabricPanel: React.FC = () => {
  const [stats, setStats] = useState<KnowledgeFabricStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queryText, setQueryText] = useState('');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [synthesisResult, setSynthesisResult] = useState<SynthesisResult | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'query' | 'create'>('overview');

  // Create node form
  const [newNode, setNewNode] = useState({
    title: '', content: '', summary: '', domain: 'technology',
    knowledge_type: 'fact', tags: '', source: '', confidence: 0.7, importance: 0.5,
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const statsRes = await request<KnowledgeFabricStats>('/knowledge-fabric/stats');
      setStats(statsRes);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleQuery = async () => {
    if (!queryText.trim()) return;
    try {
      setQueryLoading(true);
      const result = await request<QueryResult>('/knowledge-fabric/query', {
        method: 'POST',
        body: JSON.stringify({
          query_text: queryText,
          max_results: 10,
          include_related: true,
        }),
      });
      setQueryResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Query failed');
    } finally {
      setQueryLoading(false);
    }
  };

  const handleSynthesize = async () => {
    if (!queryText.trim()) return;
    try {
      setQueryLoading(true);
      const result = await request<SynthesisResult>('/knowledge-fabric/synthesize', {
        method: 'POST',
        body: JSON.stringify({ query_text: queryText, max_sources: 5 }),
      });
      setSynthesisResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Synthesis failed');
    } finally {
      setQueryLoading(false);
    }
  };

  const handleCreateNode = async () => {
    if (!newNode.title.trim()) return;
    try {
      await request('/knowledge-fabric/nodes', {
        method: 'POST',
        body: JSON.stringify({
          title: newNode.title,
          content: newNode.content,
          summary: newNode.summary,
          domain: newNode.domain,
          knowledge_type: newNode.knowledge_type,
          tags: newNode.tags.split(',').map((t: string) => t.trim()).filter(Boolean),
          source: newNode.source,
          confidence: newNode.confidence,
          importance: newNode.importance,
        }),
      });
      setNewNode({ title: '', content: '', summary: '', domain: 'technology', knowledge_type: 'fact', tags: '', source: '', confidence: 0.7, importance: 0.5 });
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  };

  const handleAutoLink = async () => {
    try {
      const result = await request<{ new_edges: number }>('/knowledge-fabric/auto-link', { method: 'POST' });
      alert(`Auto-linked ${result.new_edges} new edges`);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Auto-link failed');
    }
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header"><h2>Knowledge Fabric</h2></div>
        <div className="panel-body" style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
          <div className="loading-spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Knowledge Fabric</h2>
        <span className="panel-badge" style={{ background: stats ? '#22c55e' : '#ef4444' }}>
          {stats ? 'Active' : 'Offline'}
        </span>
      </div>

      {error && (
        <div className="error-banner" style={{ background: '#fef2f2', color: '#dc2626', padding: '12px', margin: '0 16px', borderRadius: '8px' }}>
          {error}
        </div>
      )}

      <div className="tab-bar" style={{ display: 'flex', gap: '8px', padding: '16px', borderBottom: '1px solid #e5e7eb' }}>
        {(['overview', 'query', 'create'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px', border: 'none', borderRadius: '6px', cursor: 'pointer',
              background: activeTab === tab ? '#3b82f6' : '#f3f4f6',
              color: activeTab === tab ? '#fff' : '#374151',
              fontSize: '13px', fontWeight: 500,
            }}
          >
            {tab === 'overview' ? 'Overview' : tab === 'query' ? 'Query & Synthesize' : 'Create Node'}
          </button>
        ))}
      </div>

      <div className="panel-body" style={{ padding: '16px' }}>
        {activeTab === 'overview' && stats && (
          <div>
            {/* Fabric Architecture */}
            <div className="section" style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>Fabric Architecture</h3>
              <div style={{
                padding: '16px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                borderRadius: '12px', color: '#fff',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', justifyContent: 'center' }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '24px', fontWeight: 700 }}>{stats.total_nodes}</div>
                    <div style={{ fontSize: '11px', opacity: 0.8 }}>Nodes</div>
                  </div>
                  <div style={{ fontSize: '20px', opacity: 0.5 }}>⟷</div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '24px', fontWeight: 700 }}>{stats.total_edges}</div>
                    <div style={{ fontSize: '11px', opacity: 0.8 }}>Edges</div>
                  </div>
                  <div style={{ fontSize: '20px', opacity: 0.5 }}>⟷</div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '24px', fontWeight: 700 }}>{stats.total_clusters}</div>
                    <div style={{ fontSize: '11px', opacity: 0.8 }}>Clusters</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '24px' }}>
              <div style={statCardStyle}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#10b981' }}>{stats.total_queries}</div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>Total Queries</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#8b5cf6' }}>{stats.total_tags}</div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>Unique Tags</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#f59e0b' }}>{(stats.avg_confidence * 100).toFixed(0)}%</div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>Avg Confidence</div>
              </div>
            </div>

            {/* Domain Distribution */}
            {Object.keys(stats.nodes_by_domain).length > 0 && (
              <div className="section" style={{ marginBottom: '16px' }}>
                <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>Domain Distribution</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {Object.entries(stats.nodes_by_domain).map(([domain, count]) => (
                    <div key={domain} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 12px', background: '#f9fafb', borderRadius: '8px' }}>
                      <span style={{ flex: 1, fontSize: '13px', fontWeight: 500, textTransform: 'capitalize' }}>{domain}</span>
                      <div style={{ width: '100px', height: '6px', background: '#e5e7eb', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${(count / stats.total_nodes * 100).toFixed(0)}%`,
                          height: '100%', background: '#10b981', borderRadius: '3px',
                        }} />
                      </div>
                      <span style={{ fontSize: '12px', color: '#6b7280', minWidth: '30px', textAlign: 'right' }}>{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button onClick={handleAutoLink} style={{
              width: '100%', padding: '10px', background: '#10b981', color: '#fff',
              border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer',
            }}>
              Auto-Link Knowledge Nodes
            </button>
          </div>
        )}

        {activeTab === 'query' && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <textarea
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder="Enter a query to search the knowledge fabric..."
                rows={3}
                style={{
                  width: '100%', padding: '12px', border: '1px solid #d1d5db',
                  borderRadius: '8px', fontSize: '13px', resize: 'vertical', fontFamily: 'inherit',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button onClick={handleQuery} disabled={queryLoading || !queryText.trim()} style={{
                flex: 1, padding: '10px', background: '#3b82f6', color: '#fff',
                border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer',
              }}>
                {queryLoading ? 'Searching...' : 'Search'}
              </button>
              <button onClick={handleSynthesize} disabled={queryLoading || !queryText.trim()} style={{
                flex: 1, padding: '10px', background: '#8b5cf6', color: '#fff',
                border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer',
              }}>
                {queryLoading ? 'Synthesizing...' : 'Synthesize'}
              </button>
            </div>

            {synthesisResult && (
              <div style={{ marginBottom: '16px', padding: '12px', background: '#f5f3ff', borderRadius: '8px', border: '1px solid #ddd6fe' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#5b21b6', marginBottom: '8px' }}>
                  Synthesis ({synthesisResult.total_sources_found} sources, {synthesisResult.query_time_ms.toFixed(0)}ms)
                </div>
                <div style={{ fontSize: '13px', color: '#374151', lineHeight: '1.5' }}>{synthesisResult.summary}</div>
                {synthesisResult.sources.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    {synthesisResult.sources.map((s, i) => (
                      <div key={i} style={{ fontSize: '11px', color: '#6b7280', padding: '2px 0' }}>
                        [{s.domain}] {s.title} (confidence: {(s.confidence * 100).toFixed(0)}%)
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {queryResult && (
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '12px' }}>
                  Found {queryResult.total_matches} matches in {queryResult.query_time_ms.toFixed(0)}ms
                </div>
                {queryResult.nodes.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>No results found.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {queryResult.nodes.map((node) => (
                      <div key={node.node_id} style={{ padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: '#374151' }}>{node.title}</span>
                          <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', background: '#dbeafe', color: '#1e40af' }}>{node.domain}</span>
                          <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', background: '#fef3c7', color: '#92400e' }}>{node.knowledge_type}</span>
                          <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#6b7280' }}>{(node.confidence * 100).toFixed(0)}%</span>
                        </div>
                        {node.summary && <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>{node.summary}</div>}
                        {node.tags.length > 0 && (
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {node.tags.map((tag, i) => (
                              <span key={i} style={{ padding: '1px 6px', borderRadius: '3px', fontSize: '10px', background: '#e5e7eb', color: '#374151' }}>{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'create' && (
          <div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input
                placeholder="Node Title *"
                value={newNode.title}
                onChange={(e) => setNewNode({ ...newNode, title: e.target.value })}
                style={inputStyle}
              />
              <textarea
                placeholder="Content"
                value={newNode.content}
                onChange={(e) => setNewNode({ ...newNode, content: e.target.value })}
                rows={3}
                style={{ ...inputStyle, resize: 'vertical' }}
              />
              <input
                placeholder="Summary"
                value={newNode.summary}
                onChange={(e) => setNewNode({ ...newNode, summary: e.target.value })}
                style={inputStyle}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <select value={newNode.domain} onChange={(e) => setNewNode({ ...newNode, domain: e.target.value })} style={inputStyle}>
                  {['technology', 'science', 'business', 'creative', 'personal', 'system', 'agent', 'custom'].map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
                <select value={newNode.knowledge_type} onChange={(e) => setNewNode({ ...newNode, knowledge_type: e.target.value })} style={inputStyle}>
                  {['fact', 'concept', 'procedure', 'insight', 'code', 'document', 'conversation', 'memory', 'external'].map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </select>
              </div>
              <input
                placeholder="Tags (comma-separated)"
                value={newNode.tags}
                onChange={(e) => setNewNode({ ...newNode, tags: e.target.value })}
                style={inputStyle}
              />
              <input
                placeholder="Source"
                value={newNode.source}
                onChange={(e) => setNewNode({ ...newNode, source: e.target.value })}
                style={inputStyle}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px', display: 'block' }}>Confidence: {newNode.confidence}</label>
                  <input type="range" min="0" max="1" step="0.1" value={newNode.confidence}
                    onChange={(e) => setNewNode({ ...newNode, confidence: parseFloat(e.target.value) })}
                    style={{ width: '100%' }} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px', display: 'block' }}>Importance: {newNode.importance}</label>
                  <input type="range" min="0" max="1" step="0.1" value={newNode.importance}
                    onChange={(e) => setNewNode({ ...newNode, importance: parseFloat(e.target.value) })}
                    style={{ width: '100%' }} />
                </div>
              </div>
              <button onClick={handleCreateNode} disabled={!newNode.title.trim()} style={{
                padding: '12px', background: '#10b981', color: '#fff', border: 'none',
                borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
              }}>
                Create Knowledge Node
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const statCardStyle: React.CSSProperties = {
  padding: '16px', background: '#f9fafb', borderRadius: '10px',
  border: '1px solid #e5e7eb', textAlign: 'center',
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', border: '1px solid #d1d5db',
  borderRadius: '8px', fontSize: '13px', fontFamily: 'inherit',
  boxSizing: 'border-box',
};