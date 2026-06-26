import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface ContextBundle {
  bundle_id: string;
  name: string;
  description: string;
  source_count: number;
  total_size: number;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ContextSource {
  context_id: string;
  name: string;
  source_type: string;
  content: string;
  relevance_score: number;
  created_at: string;
}

interface ContextWeaverStats {
  total_contexts: number;
  total_bundles: number;
  active_weaves: number;
  total_size_bytes: number;
  average_relevance: number;
  last_weave_at: string | null;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const ContextWeaverPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<ContextWeaverStats | null>(null);
  const [contexts, setContexts] = useState<ContextSource[]>([]);
  const [bundles, setBundles] = useState<ContextBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'add' | 'weave' | 'bundles' | 'contexts'>('overview');

  // Add context form
  const [addForm, setAddForm] = useState({
    name: '',
    source_type: 'text',
    content: '',
    tags: '',
  });
  const [adding, setAdding] = useState(false);

  // Weave form
  const [weaveForm, setWeaveForm] = useState({
    context_ids: [] as string[],
    strategy: 'relevance',
    max_tokens: 4096,
  });
  const [weaving, setWeaving] = useState(false);
  const [weaveResult, setWeaveResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, c, b] = await Promise.all([
        request<ContextWeaverStats>('/context-weaver/stats').catch(() => null),
        request<ContextSource[]>('/context-weaver/contexts').catch(() => []),
        request<ContextBundle[]>('/context-weaver/weave').catch(() => []),
      ]);
      setStats(s);
      setContexts(Array.isArray(c) ? c : (c as any)?.contexts || []);
      setBundles(Array.isArray(b) ? b : (b as any)?.bundles || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load context weaver data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAddContext = async () => {
    if (!addForm.name.trim() || !addForm.content.trim()) return;
    try {
      setAdding(true);
      const result = await request<any>('/context-weaver/contexts', {
        method: 'POST',
        body: JSON.stringify({
          name: addForm.name,
          source_type: addForm.source_type,
          content: addForm.content,
          tags: addForm.tags ? addForm.tags.split(',').map(t => t.trim()) : undefined,
        }),
      });
      toast.success(result.message || 'Context added successfully');
      setAddForm({ name: '', source_type: 'text', content: '', tags: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleWeave = async () => {
    if (weaveForm.context_ids.length === 0 && contexts.length === 0) return;
    try {
      setWeaving(true);
      setWeaveResult(null);
      const ids = weaveForm.context_ids.length > 0
        ? weaveForm.context_ids
        : contexts.slice(0, 5).map(c => c.context_id);
      const result = await request<any>('/context-weaver/weave', {
        method: 'POST',
        body: JSON.stringify({
          context_ids: ids,
          strategy: weaveForm.strategy,
          max_tokens: weaveForm.max_tokens,
        }),
      });
      setWeaveResult(result);
      toast.success(result.message || 'Context weave created successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setWeaving(false);
    }
  };

  const toggleContextSelection = (id: string) => {
    setWeaveForm(f => ({
      ...f,
      context_ids: f.context_ids.includes(id)
        ? f.context_ids.filter(cid => cid !== id)
        : [...f.context_ids, id],
    }));
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    ready: '#22c55e',
    weaving: '#3b82f6',
    draft: '#f59e0b',
    archived: '#9ca3af',
    error: '#ef4444',
  };

  const relevanceColor = (score: number): string => {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Context Weaver</h2>
          <p className="panel-subtitle">Weave multiple context sources into coherent bundles</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading context weaver data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Context Weaver</h2>
        <p className="panel-subtitle">Add, manage, and weave context sources into structured bundles for AI consumption</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_contexts}</span>
              <span className="stat-label">Contexts</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.total_bundles}</span>
              <span className="stat-label">Bundles</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.active_weaves}</span>
              <span className="stat-label">Active Weaves</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>
                {(stats.total_size_bytes / 1024).toFixed(1)} KB
              </span>
              <span className="stat-label">Total Size</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: relevanceColor(stats.average_relevance) }}>
                {(stats.average_relevance * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Avg Relevance</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'add', 'weave', 'bundles', 'contexts'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Weaver Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Contexts</span>
                <strong>{stats.total_contexts}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Bundles</span>
                <strong style={{ color: '#22c55e' }}>{stats.total_bundles}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Active Weaves</span>
                <strong style={{ color: '#3b82f6' }}>{stats.active_weaves}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Size</span>
                <strong style={{ color: '#8b5cf6' }}>{(stats.total_size_bytes / 1024).toFixed(1)} KB</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Average Relevance</span>
                <strong style={{ color: relevanceColor(stats.average_relevance) }}>
                  {(stats.average_relevance * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Last Weave</span>
                <strong>
                  {stats.last_weave_at ? new Date(stats.last_weave_at).toLocaleString() : 'Never'}
                </strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Recent Bundles</h3>
              {bundles.length === 0 ? (
                <div className="panel-empty">No bundles woven yet</div>
              ) : (
                <div className="forge-skill-list">
                  {bundles.slice(0, 5).map(bundle => (
                    <div key={bundle.bundle_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{bundle.name}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[bundle.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {bundle.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{bundle.description}</div>
                        <div>Sources: {bundle.source_count} | Size: {(bundle.total_size / 1024).toFixed(1)} KB</div>
                        <div>Created: {new Date(bundle.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <h3 style={{ marginTop: 24 }}>Recent Contexts</h3>
              {contexts.length === 0 ? (
                <div className="panel-empty">No contexts added yet</div>
              ) : (
                <div className="forge-skill-list">
                  {contexts.slice(0, 3).map(ctx => (
                    <div key={ctx.context_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{ctx.name}</div>
                        <span className="dashboard-badge" style={{
                          background: relevanceColor(ctx.relevance_score),
                          color: '#fff',
                        }}>
                          Relevance: {Math.round(ctx.relevance_score * 100)}%
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Type: {ctx.source_type}</div>
                        <div style={{ marginTop: 4, fontSize: '0.85rem', color: '#6b7280', maxHeight: 60, overflow: 'hidden' }}>
                          {ctx.content?.substring(0, 200)}{ctx.content?.length > 200 ? '...' : ''}
                        </div>
                        <div>Created: {new Date(ctx.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Add Section ── */}
      {activeSection === 'add' && (
        <div className="dashboard-section">
          <h3>Add Context Source</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Context Name</label>
              <input
                type="text"
                value={addForm.name}
                onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Context Source"
              />
            </div>
            <div className="form-group">
              <label>Source Type</label>
              <select
                value={addForm.source_type}
                onChange={e => setAddForm(f => ({ ...f, source_type: e.target.value }))}
              >
                <option value="text">Text</option>
                <option value="code">Code</option>
                <option value="document">Document</option>
                <option value="memory">Memory</option>
                <option value="url">URL</option>
                <option value="file">File</option>
              </select>
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={6}
                value={addForm.content}
                onChange={e => setAddForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the context content..."
              />
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                value={addForm.tags}
                onChange={e => setAddForm(f => ({ ...f, tags: e.target.value }))}
                placeholder="tag1, tag2, tag3"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleAddContext}
              disabled={adding || !addForm.name.trim() || !addForm.content.trim()}
            >
              {adding ? 'Adding...' : 'Add Context'}
            </button>
          </div>
        </div>
      )}

      {/* ── Weave Section ── */}
      {activeSection === 'weave' && (
        <div className="dashboard-section">
          <h3>Weave Contexts Together</h3>
          <p style={{ color: '#6b7280', fontSize: '0.9rem', marginBottom: 16 }}>
            Select multiple context sources to weave into a coherent bundle. If no contexts are selected, the first 5 will be used.
          </p>

          <div style={{ marginBottom: 16 }}>
            <h4>Select Contexts ({weaveForm.context_ids.length} selected)</h4>
            {contexts.length === 0 ? (
              <div className="panel-empty">No contexts available. Add some first.</div>
            ) : (
              <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #e2e8f0', borderRadius: 8 }}>
                {contexts.map(ctx => (
                  <div
                    key={ctx.context_id}
                    onClick={() => toggleContextSelection(ctx.context_id)}
                    style={{
                      padding: '10px 14px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      borderBottom: '1px solid #e2e8f0',
                      background: weaveForm.context_ids.includes(ctx.context_id) ? '#e8eaf6' : 'transparent',
                      transition: 'background 0.2s',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={weaveForm.context_ids.includes(ctx.context_id)}
                      onChange={() => toggleContextSelection(ctx.context_id)}
                      style={{ cursor: 'pointer' }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{ctx.name}</div>
                      <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                        {ctx.source_type} | Relevance: {Math.round(ctx.relevance_score * 100)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="skill-execute" style={{ position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Weave Strategy</label>
                <select
                  value={weaveForm.strategy}
                  onChange={e => setWeaveForm(f => ({ ...f, strategy: e.target.value }))}
                >
                  <option value="relevance">By Relevance</option>
                  <option value="chronological">Chronological</option>
                  <option value="priority">By Priority</option>
                  <option value="interleaved">Interleaved</option>
                  <option value="summary">Summary</option>
                </select>
              </div>
              <div className="form-group">
                <label>Max Tokens</label>
                <input
                  type="number"
                  min={256}
                  max={32768}
                  value={weaveForm.max_tokens}
                  onChange={e => setWeaveForm(f => ({ ...f, max_tokens: parseInt(e.target.value) || 4096 }))}
                />
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleWeave}
              disabled={weaving}
              style={{ background: '#8b5cf6' }}
            >
              {weaving ? 'Weaving...' : 'Weave Contexts'}
            </button>
          </div>

          {weaveResult && (
            <div style={{
              marginTop: 20,
              padding: 16,
              background: '#f8fafc',
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}>
              <h4>Weave Result</h4>
              <div style={{ marginTop: 8, fontSize: '0.9rem', color: '#475569' }}>
                {weaveResult.bundle_name && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Bundle:</strong> {weaveResult.bundle_name}
                  </div>
                )}
                {weaveResult.source_count !== undefined && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Sources Woven:</strong> {weaveResult.source_count}
                  </div>
                )}
                {weaveResult.weaved_content && (
                  <div style={{ marginTop: 8, padding: 8, background: '#fff', borderRadius: 4, border: '1px solid #e2e8f0' }}>
                    <strong>Woven Content:</strong>
                    <div style={{ whiteSpace: 'pre-wrap', marginTop: 4, fontSize: '0.85rem', maxHeight: 200, overflow: 'auto' }}>
                      {weaveResult.weaved_content}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Bundles Section ── */}
      {activeSection === 'bundles' && (
        <div className="dashboard-section">
          <h3>Context Bundles ({bundles.length})</h3>
          {bundles.length === 0 ? (
            <div className="panel-empty">No bundles yet. Go to the Weave tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {bundles.map(bundle => (
                <div key={bundle.bundle_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{bundle.name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[bundle.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {bundle.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{bundle.description}</div>
                    <div>Sources: {bundle.source_count} | Size: {(bundle.total_size / 1024).toFixed(1)} KB</div>
                    <div>Created: {new Date(bundle.created_at).toLocaleString()}</div>
                    <div>Updated: {new Date(bundle.updated_at).toLocaleString()}</div>
                    <div>Bundle ID: {bundle.bundle_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Contexts Section ── */}
      {activeSection === 'contexts' && (
        <div className="dashboard-section">
          <h3>Context Sources ({contexts.length})</h3>
          {contexts.length === 0 ? (
            <div className="panel-empty">No contexts yet. Go to the Add tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {contexts.map(ctx => (
                <div key={ctx.context_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{ctx.name}</div>
                    <span className="dashboard-badge" style={{
                      background: relevanceColor(ctx.relevance_score),
                      color: '#fff',
                    }}>
                      {Math.round(ctx.relevance_score * 100)}%
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Type: {ctx.source_type} | Relevance: {Math.round(ctx.relevance_score * 100)}%</div>
                    <div style={{ marginTop: 4, fontSize: '0.85rem', color: '#6b7280', maxHeight: 60, overflow: 'hidden' }}>
                      {ctx.content?.substring(0, 200)}{ctx.content?.length > 200 ? '...' : ''}
                    </div>
                    <div>Created: {new Date(ctx.created_at).toLocaleString()}</div>
                    <div>Context ID: {ctx.context_id}</div>
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

export default ContextWeaverPanel;