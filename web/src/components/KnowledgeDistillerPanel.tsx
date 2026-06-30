import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: cyan for knowledge distillation
const themeColors = {
  primary: '#0891b2',
  secondary: '#06b6d4',
  bg: '#ecfeff',
  border: '#a5f3fc',
  accent: '#cffafe',
  text: '#164e63',
};

// Enum values must match backend KnowledgeType / CompressionLevel / SourceType exactly (lowercase).
const KNOWLEDGE_TYPES = ['factual', 'procedural', 'conceptual', 'heuristic', 'pattern', 'rule'];
const COMPRESSION_LEVELS = ['light', 'moderate', 'aggressive', 'extreme'];
const SOURCE_TYPES = ['experience', 'observation', 'feedback', 'documentation', 'interaction'];

export const KnowledgeDistillerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'source' | 'distill'>('overview');

  // Sources / knowledge / transfers
  const [sources, setSources] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [selectedKnowledgeId, setSelectedKnowledgeId] = useState<string>('');
  const [knowledgeDetail, setKnowledgeDetail] = useState<any>(null);
  const [lastDistilled, setLastDistilled] = useState<any>(null);
  const [lastTransfer, setLastTransfer] = useState<any>(null);
  const [queryResults, setQueryResults] = useState<any[]>([]);

  // Source form
  const [sourceForm, setSourceForm] = useState({
    source_type: 'experience',
    agent_id: '',
    content: '',
    relevance_score: '0.5',
    metadata: '',
  });

  // Distill form
  const [distillForm, setDistillForm] = useState({
    source_ids: '',
    knowledge_type: 'factual',
    compression_level: 'moderate',
    title: '',
    tags: '',
  });

  // Transfer form
  const [transferForm, setTransferForm] = useState({
    knowledge_id: '',
    source_agent_id: '',
    target_agent_id: '',
  });

  // Query form
  const [queryForm, setQueryForm] = useState({
    agent_id: '',
    query_text: '',
    top_k: '5',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.knowledgeDistiller.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load knowledge distiller stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSources = useCallback(async () => {
    try {
      const result = await api.knowledgeDistiller.listSources();
      const list = Array.isArray(result) ? result : (result?.sources ?? []);
      setSources(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load sources');
    }
  }, [toast]);

  const loadKnowledge = useCallback(async () => {
    try {
      const result = await api.knowledgeDistiller.listKnowledge();
      const list = Array.isArray(result) ? result : (result?.knowledge ?? []);
      setKnowledge(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load knowledge');
    }
  }, [toast]);

  const loadKnowledgeDetail = useCallback(async (knowledgeId: string) => {
    if (!knowledgeId) return;
    try {
      const detail = await api.knowledgeDistiller.getKnowledge(knowledgeId);
      setKnowledgeDetail(detail);
    } catch (e: any) {
      setKnowledgeDetail(null);
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadSources();
      loadKnowledge();
    }
  }, [activeSection, loadStats, loadSources, loadKnowledge]);

  // When knowledge changes, refresh its detail
  useEffect(() => {
    if (selectedKnowledgeId) {
      loadKnowledgeDetail(selectedKnowledgeId);
    }
  }, [selectedKnowledgeId, loadKnowledgeDetail]);

  // Auto-select first knowledge when entering distill section
  useEffect(() => {
    if (activeSection === 'distill' && !selectedKnowledgeId && knowledge.length > 0) {
      setSelectedKnowledgeId(knowledge[0].knowledge_id ?? knowledge[0].id);
    }
  }, [activeSection, selectedKnowledgeId, knowledge]);

  const handleRegisterSource = async () => {
    if (!sourceForm.content.trim()) {
      toast.error('Content is required');
      return;
    }
    try {
      const payload: any = {
        source_type: sourceForm.source_type,
        content: sourceForm.content.trim(),
      };
      if (sourceForm.agent_id.trim()) payload.agent_id = sourceForm.agent_id.trim();
      if (sourceForm.relevance_score.trim() !== '') payload.relevance_score = Number(sourceForm.relevance_score);
      if (sourceForm.metadata.trim()) {
        try { payload.metadata = JSON.parse(sourceForm.metadata); } catch { payload.metadata = { text: sourceForm.metadata }; }
      }
      await api.knowledgeDistiller.registerSource(payload);
      toast.success('Source registered');
      setSourceForm({ source_type: 'experience', agent_id: '', content: '', relevance_score: '0.5', metadata: '' });
      loadSources();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDistill = async () => {
    if (!distillForm.source_ids.trim()) {
      toast.error('Source IDs are required');
      return;
    }
    try {
      const sourceIds = distillForm.source_ids.split(',').map(s => s.trim()).filter(Boolean);
      if (sourceIds.length === 0) {
        toast.error('At least one source ID is required');
        return;
      }
      const payload: any = {
        source_ids: sourceIds,
        knowledge_type: distillForm.knowledge_type,
        compression_level: distillForm.compression_level,
      };
      if (distillForm.title.trim()) payload.title = distillForm.title.trim();
      if (distillForm.tags.trim()) payload.tags = distillForm.tags.split(',').map(s => s.trim()).filter(Boolean);
      const result = await api.knowledgeDistiller.distill(payload);
      setLastDistilled(result);
      toast.success('Knowledge distilled');
      setDistillForm({ source_ids: '', knowledge_type: 'factual', compression_level: 'moderate', title: '', tags: '' });
      loadKnowledge();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTransferKnowledge = async () => {
    if (!transferForm.knowledge_id.trim() || !transferForm.source_agent_id.trim() || !transferForm.target_agent_id.trim()) {
      toast.error('Knowledge ID, source agent, and target agent are required');
      return;
    }
    try {
      const result = await api.knowledgeDistiller.transferKnowledge({
        knowledge_id: transferForm.knowledge_id.trim(),
        source_agent_id: transferForm.source_agent_id.trim(),
        target_agent_id: transferForm.target_agent_id.trim(),
      });
      setLastTransfer(result);
      toast.success('Knowledge transferred');
      setTransferForm({ knowledge_id: '', source_agent_id: '', target_agent_id: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleQueryKnowledge = async () => {
    if (!queryForm.query_text.trim()) {
      toast.error('Query text is required');
      return;
    }
    try {
      const payload: any = {
        query_text: queryForm.query_text.trim(),
        top_k: Number(queryForm.top_k),
      };
      if (queryForm.agent_id.trim()) payload.agent_id = queryForm.agent_id.trim();
      const result = await api.knowledgeDistiller.queryKnowledge(payload);
      const list = Array.isArray(result) ? result : (result?.results ?? result?.matches ?? []);
      setQueryResults(list);
      toast.success(`Query returned ${list.length} result(s)`);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>📚 Knowledge Distiller</h2>
          <p className="panel-subtitle">Register sources, distill knowledge, transfer and query across agents</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading knowledge distiller...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>📚 Knowledge Distiller</h2>
        <p className="panel-subtitle">Register sources, distill knowledge, transfer and query across agents</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_sources ?? '-'}</span><span className="stat-label">Sources</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_knowledge ?? '-'}</span><span className="stat-label">Knowledge</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_transfers ?? '-'}</span><span className="stat-label">Transfers</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.pending_transfers ?? '-'}</span><span className="stat-label">Pending</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_queries ?? '-'}</span><span className="stat-label">Queries</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'source', 'distill'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Knowledge Distiller Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Sources</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_sources ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Knowledge</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_knowledge ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Transfers</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_transfers ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Pending Transfers</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.pending_transfers ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Queries</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_queries ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Knowledge</h3>
            <button onClick={() => loadKnowledge()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {knowledge.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No knowledge recorded. Distill some from sources.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {knowledge.slice(0, 10).map((k: any) => {
                  const id = k.knowledge_id ?? k.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{k.title ?? 'untitled'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{k.knowledge_type ?? 'unknown'}]</span></div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{k.compression_level ?? 'unknown'} compression · {id}</div>
                        </div>
                        <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setActiveSection('distill'); setSelectedKnowledgeId(id); }}>Open</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Source Section */}
      {activeSection === 'source' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Source</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Source Type</label>
                <select value={sourceForm.source_type} onChange={e => setSourceForm({ ...sourceForm, source_type: e.target.value })}>
                  {SOURCE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input value={sourceForm.agent_id} onChange={e => setSourceForm({ ...sourceForm, agent_id: e.target.value })} placeholder="e.g. agent_x1" />
              </div>
              <div className="form-group">
                <label>Relevance Score (0-1)</label>
                <input value={sourceForm.relevance_score} onChange={e => setSourceForm({ ...sourceForm, relevance_score: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Content *</label>
                <textarea rows={4} value={sourceForm.content} onChange={e => setSourceForm({ ...sourceForm, content: e.target.value })} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Metadata (JSON)</label>
                <textarea rows={2} value={sourceForm.metadata} onChange={e => setSourceForm({ ...sourceForm, metadata: e.target.value })} placeholder='{"origin":"chat"}' />
              </div>
            </div>
            <button onClick={handleRegisterSource} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Source</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Sources ({sources.length})</h3>
            <button onClick={() => loadSources()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {sources.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No sources registered.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {sources.slice(0, 20).map((s: any, i: number) => {
                  const id = s.source_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{s.source_type ?? 'source'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{s.agent_id ?? 'no agent'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{(s.content ?? '').slice(0, 120)}{((s.content ?? '').length > 120) ? '…' : ''} · {id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Distill Section */}
      {activeSection === 'distill' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Distill Knowledge</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Source IDs (comma-separated) *</label>
                <input value={distillForm.source_ids} onChange={e => setDistillForm({ ...distillForm, source_ids: e.target.value })} placeholder="src_a, src_b" list="source-options" />
                <datalist id="source-options">
                  {sources.map((s: any) => <option key={s.source_id ?? s.id} value={s.source_id ?? s.id} />)}
                </datalist>
              </div>
              <div className="form-group">
                <label>Knowledge Type</label>
                <select value={distillForm.knowledge_type} onChange={e => setDistillForm({ ...distillForm, knowledge_type: e.target.value })}>
                  {KNOWLEDGE_TYPES.map(k => <option key={k} value={k}>{k}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Compression Level</label>
                <select value={distillForm.compression_level} onChange={e => setDistillForm({ ...distillForm, compression_level: e.target.value })}>
                  {COMPRESSION_LEVELS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Title</label>
                <input value={distillForm.title} onChange={e => setDistillForm({ ...distillForm, title: e.target.value })} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Tags (comma-separated)</label>
                <input value={distillForm.tags} onChange={e => setDistillForm({ ...distillForm, tags: e.target.value })} placeholder="finance, routing" />
              </div>
            </div>
            <button onClick={handleDistill} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Distill Knowledge</button>
            {lastDistilled && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(lastDistilled, null, 2)}</pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Knowledge Detail</h3>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label>Knowledge ID</label>
              <select value={selectedKnowledgeId} onChange={e => setSelectedKnowledgeId(e.target.value)}>
                <option value="">— Select knowledge —</option>
                {knowledge.map((k: any) => {
                  const id = k.knowledge_id ?? k.id;
                  return <option key={id} value={id}>{k.title ?? id}</option>;
                })}
              </select>
            </div>
            {knowledgeDetail && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(knowledgeDetail, null, 2)}</pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Transfer Knowledge</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Knowledge ID *</label>
                <input value={transferForm.knowledge_id} onChange={e => setTransferForm({ ...transferForm, knowledge_id: e.target.value })} placeholder="e.g. kn_xxx" list="knowledge-options" />
                <datalist id="knowledge-options">
                  {knowledge.map((k: any) => <option key={k.knowledge_id ?? k.id} value={k.knowledge_id ?? k.id} />)}
                </datalist>
              </div>
              <div className="form-group">
                <label>Source Agent ID *</label>
                <input value={transferForm.source_agent_id} onChange={e => setTransferForm({ ...transferForm, source_agent_id: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Target Agent ID *</label>
                <input value={transferForm.target_agent_id} onChange={e => setTransferForm({ ...transferForm, target_agent_id: e.target.value })} />
              </div>
            </div>
            <button onClick={handleTransferKnowledge} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Transfer Knowledge</button>
            {lastTransfer && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(lastTransfer, null, 2)}</pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Query Knowledge</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Query Text *</label>
                <input value={queryForm.query_text} onChange={e => setQueryForm({ ...queryForm, query_text: e.target.value })} placeholder="e.g. how to handle refunds" />
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input value={queryForm.agent_id} onChange={e => setQueryForm({ ...queryForm, agent_id: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Top K</label>
                <input value={queryForm.top_k} onChange={e => setQueryForm({ ...queryForm, top_k: e.target.value })} type="number" />
              </div>
            </div>
            <button onClick={handleQueryKnowledge} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Query</button>
            {queryResults.length > 0 && (
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {queryResults.map((r: any, i: number) => {
                  const id = r.knowledge_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{r.title ?? 'result'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>score: {r.score?.toFixed?.(2) ?? r.score ?? '-'}</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeDistillerPanel;
