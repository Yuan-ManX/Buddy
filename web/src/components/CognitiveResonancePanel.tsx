import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: fuchsia for cognitive resonance
const themeColors = {
  primary: '#c026d3',
  secondary: '#d946ef',
  bg: '#fdf4ff',
  border: '#f5d0fe',
  accent: '#fae8ff',
  text: '#701a75',
};

// Enum values must match backend ResonanceType / ResonanceMode / DetectionMethod / AmplificationStatus exactly (uppercase).
const RESONANCE_TYPES = ['STRUCTURAL', 'SEMANTIC', 'CAUSAL', 'TEMPORAL', 'FUNCTIONAL', 'EMOTIONAL'];
const RESONANCE_MODES = ['CONSTRUCTIVE', 'DESTRUCTIVE', 'COUPLED', 'HARMONIC'];
const DETECTION_METHODS = ['CROSS_CORRELATION', 'PATTERN_MATCHING', 'EIGENVALUE', 'GRAPH_ALIGNMENT', 'STATISTICAL'];
const AMPLIFICATION_STATUS = ['DORMANT', 'BUILDING', 'PEAK', 'DECAYING', 'DAMPED'];

// Map an amplification status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  DORMANT: '#9ca3af',
  BUILDING: '#0ea5e9',
  PEAK: '#c026d3',
  DECAYING: '#f59e0b',
  DAMPED: '#dc2626',
};

export const CognitiveResonancePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'context' | 'event'>('overview');

  // Contexts / events / clusters
  const [contexts, setContexts] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [clusters, setClusters] = useState<any[]>([]);
  const [amplifyResult, setAmplifyResult] = useState<any>(null);
  const [clusterResult, setClusterResult] = useState<any>(null);
  const [insightResult, setInsightResult] = useState<any>(null);
  const [networkResult, setNetworkResult] = useState<any>(null);

  // Register context form
  const [contextForm, setContextForm] = useState({
    agent_id: '',
    domain: '',
    description: '',
  });

  // Register concept form
  const [conceptForm, setConceptForm] = useState({
    context_id: '',
    concept: '',
    attributes: '',
  });

  // Detect resonance form
  const [detectForm, setDetectForm] = useState({
    context_id: '',
    concept_a: '',
    concept_b: '',
    resonance_type: 'SEMANTIC',
    method: 'CROSS_CORRELATION',
  });

  // Measure amplification form
  const [amplifyForm, setAmplifyForm] = useState({ event_id: '' });

  // Cluster form
  const [clusterForm, setClusterForm] = useState({
    context_id: '',
    threshold: '0.5',
  });

  // Generate insight form
  const [insightForm, setInsightForm] = useState({ cluster_id: '' });

  // Map network form
  const [networkForm, setNetworkForm] = useState({ context_id: '' });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveResonance.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive resonance stats');
    } finally {
      setLoading(false);
    }
  };

  const loadContexts = async () => {
    try {
      const result = await api.cognitiveResonance.listContexts();
      const list = Array.isArray(result) ? result : (result?.contexts ?? []);
      setContexts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load contexts');
    }
  };

  const loadEvents = async () => {
    try {
      const list: any[] = [];
      // Events are scoped per context; aggregate across loaded contexts.
      for (const c of contexts) {
        const cid = c.context_id ?? c.id;
        if (!cid) continue;
        try {
          const result = await api.cognitiveResonance.listEvents(cid);
          const partial = Array.isArray(result) ? result : (result?.events ?? []);
          list.push(...partial);
        } catch { /* skip contexts without events */ }
      }
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  };

  const loadClusters = async () => {
    try {
      const result = await api.cognitiveResonance.listClusters();
      const list = Array.isArray(result) ? result : (result?.clusters ?? []);
      setClusters(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load clusters');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + contexts when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadContexts();
      loadClusters();
    }
  }, [activeSection]);

  // After contexts are loaded, aggregate events for the overview list
  useEffect(() => {
    if (activeSection === 'overview' && contexts.length > 0) {
      loadEvents();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contexts, activeSection]);

  const handleRegisterContext = async () => {
    if (!contextForm.agent_id.trim() || !contextForm.domain.trim()) {
      toast.error('Agent ID and domain are required');
      return;
    }
    const payload: any = {
      agent_id: contextForm.agent_id.trim(),
      domain: contextForm.domain.trim(),
    };
    if (contextForm.description.trim()) payload.description = contextForm.description.trim();
    try {
      await api.cognitiveResonance.registerContext(payload);
      toast.success('Context registered');
      setContextForm({ agent_id: '', domain: '', description: '' });
      await loadContexts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRegisterConcept = async () => {
    if (!conceptForm.context_id.trim() || !conceptForm.concept.trim()) {
      toast.error('Context ID and concept are required');
      return;
    }
    const payload: any = { concept: conceptForm.concept.trim() };
    if (conceptForm.attributes.trim()) {
      try { payload.attributes = JSON.parse(conceptForm.attributes); }
      catch { toast.error('Attributes must be valid JSON'); return; }
    }
    try {
      await api.cognitiveResonance.registerConcept(conceptForm.context_id.trim(), payload);
      toast.success('Concept registered');
      setConceptForm({ context_id: '', concept: '', attributes: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDetectResonance = async () => {
    if (!detectForm.context_id.trim() || !detectForm.concept_a.trim() || !detectForm.concept_b.trim()) {
      toast.error('Context ID and both concepts are required');
      return;
    }
    const payload: any = {
      concept_a: detectForm.concept_a.trim(),
      concept_b: detectForm.concept_b.trim(),
      resonance_type: detectForm.resonance_type,
      method: detectForm.method,
    };
    try {
      await api.cognitiveResonance.detectResonance(detectForm.context_id.trim(), payload);
      toast.success('Resonance detected');
      setDetectForm({ context_id: '', concept_a: '', concept_b: '', resonance_type: 'SEMANTIC', method: 'CROSS_CORRELATION' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMeasureAmplification = async () => {
    if (!amplifyForm.event_id.trim()) {
      toast.error('Event ID is required');
      return;
    }
    try {
      const result = await api.cognitiveResonance.measureAmplification(amplifyForm.event_id.trim());
      setAmplifyResult(result);
      toast.success('Amplification measured');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCluster = async () => {
    if (!clusterForm.context_id.trim()) {
      toast.error('Context ID is required');
      return;
    }
    const threshold = clusterForm.threshold.trim() ? Number(clusterForm.threshold) : undefined;
    try {
      const result = await api.cognitiveResonance.clusterResonances(clusterForm.context_id.trim(), threshold);
      setClusterResult(result);
      toast.success('Resonances clustered');
      await loadClusters();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGenerateInsight = async () => {
    if (!insightForm.cluster_id.trim()) {
      toast.error('Cluster ID is required');
      return;
    }
    try {
      const result = await api.cognitiveResonance.generateInsight(insightForm.cluster_id.trim());
      setInsightResult(result);
      toast.success('Insight generated');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMapNetwork = async () => {
    if (!networkForm.context_id.trim()) {
      toast.error('Context ID is required');
      return;
    }
    try {
      const result = await api.cognitiveResonance.mapNetwork(networkForm.context_id.trim());
      setNetworkResult(result);
      toast.success('Network mapped');
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
          <h2>🎵 Cognitive Resonance</h2>
          <p className="panel-subtitle">Detect resonant concept pairs, measure amplification, and cluster networks</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive resonance...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🎵 Cognitive Resonance</h2>
        <p className="panel-subtitle">Detect resonant concept pairs, measure amplification, and cluster networks</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_contexts ?? '-'}</span><span className="stat-label">Contexts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_concepts ?? '-'}</span><span className="stat-label">Concepts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_clusters ?? '-'}</span><span className="stat-label">Clusters</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_amplifications ?? '-'}</span><span className="stat-label">Amplifications</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'context', 'event'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Resonance Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Contexts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_contexts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Concepts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_concepts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_events ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Clusters</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_clusters ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Amplifications</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_amplifications ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Clusters</h3>
            <button onClick={() => loadClusters()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {clusters.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No clusters recorded. Cluster events in the Event section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {clusters.slice(0, 10).map((c: any, i: number) => {
                  const id = c.cluster_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>cluster {id}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>context: {c.context_id ?? '-'}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Context Section */}
      {activeSection === 'context' && (
        <div className="dashboard-section">
          {/* Register Context */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Context</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={contextForm.agent_id} onChange={e => setContextForm({ ...contextForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Domain *</label>
                <input value={contextForm.domain} onChange={e => setContextForm({ ...contextForm, domain: e.target.value })} placeholder="e.g. causal_reasoning" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={contextForm.description} onChange={e => setContextForm({ ...contextForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleRegisterContext} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Context</button>
          </div>

          {/* Register Concept */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Concept</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={conceptForm.context_id} onChange={e => setConceptForm({ ...conceptForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Concept *</label>
                <input value={conceptForm.concept} onChange={e => setConceptForm({ ...conceptForm, concept: e.target.value })} placeholder="e.g. causal_link" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Attributes (JSON)</label>
                <input value={conceptForm.attributes} onChange={e => setConceptForm({ ...conceptForm, attributes: e.target.value })} placeholder='{"strength": 0.7, "novelty": 0.4}' />
              </div>
            </div>
            <button onClick={handleRegisterConcept} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Concept</button>
          </div>

          {/* Map Network */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Map Network</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={networkForm.context_id} onChange={e => setNetworkForm({ ...networkForm, context_id: e.target.value })} placeholder="context id" />
              </div>
            </div>
            <button onClick={handleMapNetwork} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Map Network</button>
            {networkResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(networkResult, null, 2)}</pre>
            )}
          </div>

          {/* Contexts List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Contexts ({contexts.length})</h3>
            <button onClick={() => loadContexts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {contexts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No contexts recorded. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {contexts.slice(0, 30).map((c: any, i: number) => {
                  const id = c.context_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{c.domain ?? 'no_domain'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                      {c.description && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{c.description}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Event Section */}
      {activeSection === 'event' && (
        <div className="dashboard-section">
          {/* Detect Resonance */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Detect Resonance</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={detectForm.context_id} onChange={e => setDetectForm({ ...detectForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Concept A *</label>
                <input value={detectForm.concept_a} onChange={e => setDetectForm({ ...detectForm, concept_a: e.target.value })} placeholder="first concept" />
              </div>
              <div className="form-group">
                <label>Concept B *</label>
                <input value={detectForm.concept_b} onChange={e => setDetectForm({ ...detectForm, concept_b: e.target.value })} placeholder="second concept" />
              </div>
              <div className="form-group">
                <label>Resonance Type</label>
                <select value={detectForm.resonance_type} onChange={e => setDetectForm({ ...detectForm, resonance_type: e.target.value })}>
                  {RESONANCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Method</label>
                <select value={detectForm.method} onChange={e => setDetectForm({ ...detectForm, method: e.target.value })}>
                  {DETECTION_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleDetectResonance} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Detect Resonance</button>
          </div>

          {/* Measure Amplification */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Measure Amplification</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Event ID *</label>
                <input value={amplifyForm.event_id} onChange={e => setAmplifyForm({ ...amplifyForm, event_id: e.target.value })} placeholder="event id" />
              </div>
            </div>
            <button onClick={handleMeasureAmplification} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Measure</button>
            {amplifyResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(amplifyResult, null, 2)}</pre>
            )}
          </div>

          {/* Cluster */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Cluster Resonances</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={clusterForm.context_id} onChange={e => setClusterForm({ ...clusterForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Threshold</label>
                <input value={clusterForm.threshold} onChange={e => setClusterForm({ ...clusterForm, threshold: e.target.value })} type="number" min="0" max="1" step="0.05" />
              </div>
            </div>
            <button onClick={handleCluster} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Cluster</button>
            {clusterResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(clusterResult, null, 2)}</pre>
            )}
          </div>

          {/* Generate Insight */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Generate Insight</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Cluster ID *</label>
                <input value={insightForm.cluster_id} onChange={e => setInsightForm({ ...insightForm, cluster_id: e.target.value })} placeholder="cluster id" />
              </div>
            </div>
            <button onClick={handleGenerateInsight} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Generate Insight</button>
            {insightResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(insightResult, null, 2)}</pre>
            )}
          </div>

          {/* Events List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Events ({events.length})</h3>
            <button onClick={() => loadEvents()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {events.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No events recorded. Detect resonance above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {events.slice(0, 30).map((e: any, i: number) => {
                  const id = e.event_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{e.concept_a ?? '-'} ↔ {e.concept_b ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>context: {e.context_id ?? '-'} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.resonance_type && renderBadge(e.resonance_type, themeColors.secondary)}
                          {e.mode && renderBadge(e.mode, themeColors.primary)}
                          {e.status && renderBadge(e.status, statusColor(e.status))}
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

export default CognitiveResonancePanel;
