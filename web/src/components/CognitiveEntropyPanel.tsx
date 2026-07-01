import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: teal for cognitive entropy
const themeColors = {
  primary: '#0d9488',
  secondary: '#14b8a6',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#134e4a',
};

// Enum values must match backend EntropyKind / EntropyRegime / FluxDirection / InferencePrinciple / CompressionStatus exactly (uppercase).
const ENTROPY_KINDS = ['BELIEF', 'REASONING', 'DECISION', 'ATTENTION', 'KNOWLEDGE'];
const ENTROPY_REGIMES = ['RIGID', 'ORDERED', 'BALANCED', 'DISORDERED', 'CHAOTIC'];
const FLUX_DIRECTIONS = ['INCREASING', 'DECREASING', 'STABLE', 'FLUCTUATING'];
const INFERENCE_PRINCIPLES = ['MAXIMUM_ENTROPY', 'MINIMUM_ENTROPY', 'PRINCIPLE_OF_INDIFFERENCE', 'CROSS_ENTROPY_MIN'];
const COMPRESSION_STATUS = ['UNCOMPRESSED', 'PARTIAL', 'COMPRESSED', 'LOSSY'];

// Map a compression status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  UNCOMPRESSED: '#9ca3af',
  PARTIAL: '#0ea5e9',
  COMPRESSED: '#0d9488',
  LOSSY: '#dc2626',
};

export const CognitiveEntropyPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'sample' | 'inference'>('overview');

  // Samples / fluxes / inferences
  const [samples, setSamples] = useState<any[]>([]);
  const [fluxes, setFluxes] = useState<any[]>([]);
  const [inferences, setInferences] = useState<any[]>([]);
  const [compressionResult, setCompressionResult] = useState<any>(null);

  // Sample distribution form
  const [sampleForm, setSampleForm] = useState({
    agent_id: '',
    kind: 'BELIEF',
    distribution: '',
  });

  // Record flux form
  const [fluxForm, setFluxForm] = useState({
    agent_id: '',
    kind: 'BELIEF',
    current_entropy: '',
  });

  // Infer distribution form
  const [inferenceForm, setInferenceForm] = useState({
    agent_id: '',
    principle: 'MAXIMUM_ENTROPY',
    prior: '',
    evidence: '',
    rationale: '',
  });

  // Compress payload form
  const [compressionForm, setCompressionForm] = useState({
    agent_id: '',
    source_payload: '',
    entropy_before: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveEntropy.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive entropy stats');
    } finally {
      setLoading(false);
    }
  };

  const loadSamples = async () => {
    try {
      const result = await api.cognitiveEntropy.listSamples();
      const list = Array.isArray(result) ? result : (result?.samples ?? []);
      setSamples(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load samples');
    }
  };

  const loadFluxes = async () => {
    try {
      const result = await api.cognitiveEntropy.listFluxes();
      const list = Array.isArray(result) ? result : (result?.fluxes ?? []);
      setFluxes(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load fluxes');
    }
  };

  const loadInferences = async () => {
    try {
      const result = await api.cognitiveEntropy.listInferences();
      const list = Array.isArray(result) ? result : (result?.inferences ?? []);
      setInferences(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load inferences');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadSamples();
      loadFluxes();
      loadInferences();
    }
  }, [activeSection]);

  const handleSampleDistribution = async () => {
    if (!sampleForm.agent_id.trim() || !sampleForm.distribution.trim()) {
      toast.error('Agent ID and distribution are required');
      return;
    }
    let distribution: Record<string, number>;
    try { distribution = JSON.parse(sampleForm.distribution); }
    catch { toast.error('Distribution must be valid JSON'); return; }
    const payload: any = {
      agent_id: sampleForm.agent_id.trim(),
      kind: sampleForm.kind,
      distribution,
    };
    try {
      await api.cognitiveEntropy.sampleDistribution(payload);
      toast.success('Distribution sampled');
      setSampleForm({ agent_id: '', kind: 'BELIEF', distribution: '' });
      await loadSamples();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordFlux = async () => {
    if (!fluxForm.agent_id.trim() || !fluxForm.current_entropy.trim()) {
      toast.error('Agent ID and current entropy are required');
      return;
    }
    const payload: any = {
      agent_id: fluxForm.agent_id.trim(),
      kind: fluxForm.kind,
      current_entropy: Number(fluxForm.current_entropy),
    };
    try {
      await api.cognitiveEntropy.recordFlux(payload);
      toast.success('Flux recorded');
      setFluxForm({ agent_id: '', kind: 'BELIEF', current_entropy: '' });
      await loadFluxes();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleInferDistribution = async () => {
    if (!inferenceForm.agent_id.trim() || !inferenceForm.prior.trim()) {
      toast.error('Agent ID and prior are required');
      return;
    }
    let prior: Record<string, number>;
    try { prior = JSON.parse(inferenceForm.prior); }
    catch { toast.error('Prior must be valid JSON'); return; }
    const payload: any = {
      agent_id: inferenceForm.agent_id.trim(),
      principle: inferenceForm.principle,
      prior,
    };
    if (inferenceForm.evidence.trim()) {
      try { payload.evidence = JSON.parse(inferenceForm.evidence); }
      catch { toast.error('Evidence must be valid JSON'); return; }
    }
    if (inferenceForm.rationale.trim()) payload.rationale = inferenceForm.rationale.trim();
    try {
      await api.cognitiveEntropy.inferDistribution(payload);
      toast.success('Distribution inferred');
      setInferenceForm({ agent_id: '', principle: 'MAXIMUM_ENTROPY', prior: '', evidence: '', rationale: '' });
      await loadInferences();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCompressPayload = async () => {
    if (!compressionForm.agent_id.trim() || !compressionForm.source_payload.trim() || !compressionForm.entropy_before.trim()) {
      toast.error('Agent ID, source payload, and entropy before are required');
      return;
    }
    const payload: any = {
      agent_id: compressionForm.agent_id.trim(),
      source_payload: compressionForm.source_payload,
      entropy_before: Number(compressionForm.entropy_before),
    };
    try {
      const result = await api.cognitiveEntropy.compressPayload(payload);
      setCompressionResult(result);
      toast.success('Payload compressed');
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
          <h2>🌀 Cognitive Entropy</h2>
          <p className="panel-subtitle">Sample distributions, record flux, and infer via entropy principles</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive entropy...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌀 Cognitive Entropy</h2>
        <p className="panel-subtitle">Sample distributions, record flux, and infer via entropy principles</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_samples ?? '-'}</span><span className="stat-label">Samples</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_flux_records ?? '-'}</span><span className="stat-label">Flux Records</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_inferences ?? '-'}</span><span className="stat-label">Inferences</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_compressions ?? '-'}</span><span className="stat-label">Compressions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_shannon_entropy ?? '-'}</span><span className="stat-label">Avg Shannon</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_normalized_entropy ?? '-'}</span><span className="stat-label">Avg Normalized</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'sample', 'inference'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Entropy Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Samples</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_samples ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Flux Records</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_flux_records ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Inferences</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_inferences ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Compressions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_compressions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Shannon Entropy</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_shannon_entropy ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Normalized Entropy</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_normalized_entropy ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Samples</h3>
            <button onClick={() => loadSamples()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {samples.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No samples recorded. Sample a distribution in the Sample section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {samples.slice(0, 10).map((s: any, i: number) => {
                  const id = s.sample_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>sample {id} · entropy: {s.shannon_entropy ?? s.entropy ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.kind && renderBadge(s.kind, themeColors.secondary)}
                          {s.regime && renderBadge(s.regime, statusColor(s.regime))}
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

      {/* Sample Section */}
      {activeSection === 'sample' && (
        <div className="dashboard-section">
          {/* Sample Distribution */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Sample Distribution</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={sampleForm.agent_id} onChange={e => setSampleForm({ ...sampleForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Kind</label>
                <select value={sampleForm.kind} onChange={e => setSampleForm({ ...sampleForm, kind: e.target.value })}>
                  {ENTROPY_KINDS.map(k => <option key={k} value={k}>{k}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Distribution (JSON) *</label>
                <textarea value={sampleForm.distribution} onChange={e => setSampleForm({ ...sampleForm, distribution: e.target.value })} placeholder='{"a":0.5,"b":0.5}' rows={3} style={{ width: '100%', fontFamily: 'monospace' }} />
              </div>
            </div>
            <button onClick={handleSampleDistribution} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Sample Distribution</button>
          </div>

          {/* Record Flux */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Flux</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={fluxForm.agent_id} onChange={e => setFluxForm({ ...fluxForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Kind</label>
                <select value={fluxForm.kind} onChange={e => setFluxForm({ ...fluxForm, kind: e.target.value })}>
                  {ENTROPY_KINDS.map(k => <option key={k} value={k}>{k}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Current Entropy *</label>
                <input value={fluxForm.current_entropy} onChange={e => setFluxForm({ ...fluxForm, current_entropy: e.target.value })} type="number" step="0.001" placeholder="e.g. 0.81" />
              </div>
            </div>
            <button onClick={handleRecordFlux} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Flux</button>
          </div>

          {/* Fluxes List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Fluxes ({fluxes.length})</h3>
            <button onClick={() => loadFluxes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {fluxes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No flux records. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {fluxes.slice(0, 30).map((f: any, i: number) => {
                  const id = f.flux_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'} · entropy: {f.current_entropy ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>flux {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.kind && renderBadge(f.kind, themeColors.secondary)}
                          {f.direction && renderBadge(f.direction, themeColors.primary)}
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

      {/* Inference Section */}
      {activeSection === 'inference' && (
        <div className="dashboard-section">
          {/* Infer Distribution */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Infer Distribution</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={inferenceForm.agent_id} onChange={e => setInferenceForm({ ...inferenceForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Principle</label>
                <select value={inferenceForm.principle} onChange={e => setInferenceForm({ ...inferenceForm, principle: e.target.value })}>
                  {INFERENCE_PRINCIPLES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Prior (JSON) *</label>
                <textarea value={inferenceForm.prior} onChange={e => setInferenceForm({ ...inferenceForm, prior: e.target.value })} placeholder='{"a":0.5,"b":0.5}' rows={3} style={{ width: '100%', fontFamily: 'monospace' }} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Evidence (JSON)</label>
                <textarea value={inferenceForm.evidence} onChange={e => setInferenceForm({ ...inferenceForm, evidence: e.target.value })} placeholder='{"a":0.7,"b":0.3}' rows={3} style={{ width: '100%', fontFamily: 'monospace' }} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input value={inferenceForm.rationale} onChange={e => setInferenceForm({ ...inferenceForm, rationale: e.target.value })} placeholder="optional rationale" />
              </div>
            </div>
            <button onClick={handleInferDistribution} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Infer Distribution</button>
          </div>

          {/* Compress Payload */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Compress Payload</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={compressionForm.agent_id} onChange={e => setCompressionForm({ ...compressionForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Source Payload *</label>
                <input value={compressionForm.source_payload} onChange={e => setCompressionForm({ ...compressionForm, source_payload: e.target.value })} type="text" placeholder="e.g. sample text payload" />
              </div>
              <div className="form-group">
                <label>Entropy Before *</label>
                <input value={compressionForm.entropy_before} onChange={e => setCompressionForm({ ...compressionForm, entropy_before: e.target.value })} type="number" step="0.001" placeholder="e.g. 2.3" />
              </div>
            </div>
            <button onClick={handleCompressPayload} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Compress Payload</button>
            {compressionResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(compressionResult, null, 2)}</pre>
            )}
          </div>

          {/* Inferences List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Inferences ({inferences.length})</h3>
            <button onClick={() => loadInferences()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {inferences.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No inferences recorded. Infer one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {inferences.slice(0, 30).map((inf: any, i: number) => {
                  const id = inf.inference_id ?? inf.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {inf.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>inference {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {inf.principle && renderBadge(inf.principle, themeColors.secondary)}
                        </div>
                      </div>
                      {inf.rationale && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{inf.rationale}</div>
                      )}
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

export default CognitiveEntropyPanel;
