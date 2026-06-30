import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: purple for concept formation
const themeColors = {
  primary: '#7c3aed',
  secondary: '#8b5cf6',
  bg: '#faf5ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

// Enum values must match backend ConceptType / AbstractionLevel / FormationStatus exactly (lowercase).
const CONCEPT_TYPES = ['concrete', 'abstract', 'procedural', 'relational', 'composite'];
const ABSTRACTION_LEVELS = ['instance', 'prototype', 'category', 'supercategory', 'root'];
const FORMATION_STATUS = ['pending', 'clustering', 'formed', 'validated', 'refined', 'deprecated'];
const CLUSTER_METHODS = ['kmeans', 'hierarchical', 'dbscan', 'agglomerative', 'manual'];
const SIMILARITY_METRICS = ['cosine', 'euclidean', 'jaccard', 'hamming', 'custom'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  pending: '#9ca3af',
  clustering: '#2563eb',
  formed: '#059669',
  validated: '#7c3aed',
  refined: '#db2777',
  deprecated: '#dc2626',
};

export const ConceptFormationPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'instance' | 'concept'>('overview');

  // Instances / concepts
  const [instances, setInstances] = useState<any[]>([]);
  const [concepts, setConcepts] = useState<any[]>([]);

  // Instance form
  const [instanceForm, setInstanceForm] = useState({
    agent_id: '',
    features: '',
    source: '',
    confidence: '1.0',
  });

  // Concept form
  const [conceptForm, setConceptForm] = useState({
    name: '',
    concept_type: 'abstract',
    abstraction_level: 'category',
    cluster_method: 'kmeans',
    similarity_metric: 'cosine',
    source_instance_ids: '',
    description: '',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.conceptFormation.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load concept formation stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadInstances = useCallback(async () => {
    try {
      const result = await api.conceptFormation.listInstances();
      const list = Array.isArray(result) ? result : (result?.instances ?? []);
      setInstances(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load instances');
    }
  }, [toast]);

  const loadConcepts = useCallback(async () => {
    try {
      const result = await api.conceptFormation.listConcepts();
      const list = Array.isArray(result) ? result : (result?.concepts ?? []);
      setConcepts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load concepts');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadInstances();
      loadConcepts();
    }
  }, [activeSection, loadStats, loadInstances, loadConcepts]);

  const handleRegisterInstance = async () => {
    if (!instanceForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    let features: any = {};
    if (instanceForm.features.trim() !== '') {
      try { features = JSON.parse(instanceForm.features); }
      catch { toast.error('Features must be valid JSON'); return; }
    }
    try {
      const payload: any = {
        agent_id: instanceForm.agent_id.trim(),
        features,
      };
      if (instanceForm.source.trim()) payload.source = instanceForm.source.trim();
      if (instanceForm.confidence.trim() !== '') payload.confidence = Number(instanceForm.confidence);
      await api.conceptFormation.registerInstance(payload);
      toast.success('Instance registered');
      setInstanceForm({ agent_id: '', features: '', source: '', confidence: '1.0' });
      await loadInstances();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFormConcept = async () => {
    if (!conceptForm.name.trim()) {
      toast.error('Concept name is required');
      return;
    }
    try {
      const payload: any = {
        name: conceptForm.name.trim(),
        concept_type: conceptForm.concept_type,
        abstraction_level: conceptForm.abstraction_level,
        cluster_method: conceptForm.cluster_method,
        similarity_metric: conceptForm.similarity_metric,
      };
      if (conceptForm.description.trim()) payload.description = conceptForm.description.trim();
      if (conceptForm.source_instance_ids.trim()) {
        payload.source_instance_ids = conceptForm.source_instance_ids
          .split(',').map(s => s.trim()).filter(Boolean);
      }
      await api.conceptFormation.formConcept(payload);
      toast.success('Concept formed');
      setConceptForm({
        name: '',
        concept_type: 'abstract',
        abstraction_level: 'category',
        cluster_method: 'kmeans',
        similarity_metric: 'cosine',
        source_instance_ids: '',
        description: '',
      });
      await loadConcepts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeleteConcept = async (conceptId: string) => {
    if (!conceptId) return;
    try {
      await api.conceptFormation.deleteConcept(conceptId);
      toast.success('Concept deleted');
      await loadConcepts();
    } catch (e: any) { toast.error(e.message); }
  };

  const renderBadge = (value: string, color: string) => (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 10,
      fontSize: 11,
      fontWeight: 600,
      color: '#fff',
      background: color,
      marginRight: 4,
    }}>{value}</span>
  );

  const statusColor = (s: string) => STATUS_COLORS[s] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🧠 Concept Formation</h2>
          <p className="panel-subtitle">Register instances, form concepts, and build concept hierarchies</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading concept formation...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧠 Concept Formation</h2>
        <p className="panel-subtitle">Register instances, form concepts, and build concept hierarchies</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_instances ?? '-'}</span><span className="stat-label">Instances</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_concepts ?? '-'}</span><span className="stat-label">Concepts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_clusters ?? '-'}</span><span className="stat-label">Clusters</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_hierarchies ?? '-'}</span><span className="stat-label">Hierarchies</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.pending_count ?? '-'}</span><span className="stat-label">Pending</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'instance', 'concept'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Concept Formation Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Instances</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_instances ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Concepts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_concepts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Clusters</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_clusters ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Hierarchies</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_hierarchies ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Pending</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.pending_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Concepts</h3>
            <button onClick={() => loadConcepts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {concepts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No concepts recorded. Form one in the Concept section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {concepts.slice(0, 10).map((c: any, i: number) => {
                  const id = c.concept_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{c.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{c.description ?? ''} · {id}</div>
                        </div>
                        <div>
                          {c.concept_type && renderBadge(c.concept_type, themeColors.secondary)}
                          {c.formation_status && renderBadge(c.formation_status, statusColor(c.formation_status))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Instance Section */}
      {activeSection === 'instance' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Instance</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={instanceForm.agent_id} onChange={e => setInstanceForm({ ...instanceForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Source</label>
                <input value={instanceForm.source} onChange={e => setInstanceForm({ ...instanceForm, source: e.target.value })} placeholder="e.g. observation" />
              </div>
              <div className="form-group">
                <label>Confidence</label>
                <input value={instanceForm.confidence} onChange={e => setInstanceForm({ ...instanceForm, confidence: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Features (JSON)</label>
                <input value={instanceForm.features} onChange={e => setInstanceForm({ ...instanceForm, features: e.target.value })} placeholder='{"color": "red", "weight": 12}' />
              </div>
            </div>
            <button onClick={handleRegisterInstance} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Instance</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Instances ({instances.length})</h3>
            <button onClick={() => loadInstances()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {instances.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No instances recorded. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {instances.slice(0, 30).map((inst: any, i: number) => {
                  const id = inst.instance_id ?? inst.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{inst.agent_id ?? 'unknown_agent'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{inst.source ?? 'no_source'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>confidence: {inst.confidence ?? '-'} · {id}</div>
                      {inst.features && (
                        <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 6, overflow: 'auto', maxHeight: 100, fontSize: 11 }}>{JSON.stringify(inst.features, null, 2)}</pre>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Concept Section */}
      {activeSection === 'concept' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Form Concept</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={conceptForm.name} onChange={e => setConceptForm({ ...conceptForm, name: e.target.value })} placeholder="e.g. vehicle" />
              </div>
              <div className="form-group">
                <label>Concept Type</label>
                <select value={conceptForm.concept_type} onChange={e => setConceptForm({ ...conceptForm, concept_type: e.target.value })}>
                  {CONCEPT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Abstraction Level</label>
                <select value={conceptForm.abstraction_level} onChange={e => setConceptForm({ ...conceptForm, abstraction_level: e.target.value })}>
                  {ABSTRACTION_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Cluster Method</label>
                <select value={conceptForm.cluster_method} onChange={e => setConceptForm({ ...conceptForm, cluster_method: e.target.value })}>
                  {CLUSTER_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Similarity Metric</label>
                <select value={conceptForm.similarity_metric} onChange={e => setConceptForm({ ...conceptForm, similarity_metric: e.target.value })}>
                  {SIMILARITY_METRICS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Source Instance IDs (comma-separated)</label>
                <input value={conceptForm.source_instance_ids} onChange={e => setConceptForm({ ...conceptForm, source_instance_ids: e.target.value })} placeholder="inst_1, inst_2, inst_3" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={conceptForm.description} onChange={e => setConceptForm({ ...conceptForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleFormConcept} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Form Concept</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Concepts ({concepts.length})</h3>
            <button onClick={() => loadConcepts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {concepts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No concepts recorded. Form one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {concepts.slice(0, 30).map((c: any, i: number) => {
                  const id = c.concept_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{c.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{c.description ?? ''} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.concept_type && renderBadge(c.concept_type, themeColors.secondary)}
                          {c.abstraction_level && renderBadge(c.abstraction_level, '#6366f1')}
                          {c.formation_status && renderBadge(c.formation_status, statusColor(c.formation_status))}
                          <button className="btn-sm" style={{ background: '#dc2626', color: '#fff', marginLeft: 4 }} onClick={() => handleDeleteConcept(id)}>Delete</button>
                        </div>
                      </div>
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

export default ConceptFormationPanel;
