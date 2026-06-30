import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: amber for cognitive affordance
const themeColors = {
  primary: '#d97706',
  secondary: '#f59e0b',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

// Enum values must match backend AffordanceSource / AffordanceStatus / ConstraintType / SignatureType / RankingMetric exactly (uppercase).
const AFFORDANCE_SOURCES = ['TOOL', 'ENVIRONMENT', 'CONTEXT', 'SOCIAL', 'ARTIFACT', 'INTERFACE'];
const AFFORDANCE_STATUS = ['PERCEIVED', 'VALIDATED', 'INVALIDATED', 'EXECUTED', 'FAILED'];
const CONSTRAINT_TYPES = ['PRECONDITION', 'RESOURCE', 'SAFETY', 'TEMPORAL', 'PERMISSION'];
const SIGNATURE_TYPES = ['PERCEPTUAL', 'STRUCTURAL', 'FUNCTIONAL', 'CONTEXTUAL'];
const RANKING_METRICS = ['UTILITY', 'EFFORT', 'RISK', 'GOAL_ALIGNMENT'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  PERCEIVED: '#9ca3af',
  VALIDATED: '#059669',
  INVALIDATED: '#dc2626',
  EXECUTED: '#0d9488',
  FAILED: '#b91c1c',
};

export const CognitiveAffordancePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'context' | 'affordance'>('overview');

  // Contexts / affordances / selected context / ranking result
  const [contexts, setContexts] = useState<any[]>([]);
  const [affordances, setAffordances] = useState<any[]>([]);
  const [selectedContext, setSelectedContext] = useState<string>('');
  const [rankResult, setRankResult] = useState<any>(null);
  const [mapResult, setMapResult] = useState<any>(null);

  // Context form
  const [contextForm, setContextForm] = useState({
    agent_id: '',
    environment_id: '',
    description: '',
  });

  // Perceive affordance form
  const [perceiveForm, setPerceiveForm] = useState({
    name: '',
    source: 'TOOL',
    description: '',
    effort: '',
    utility: '',
    risk: '',
  });

  // Validate form
  const [validateForm, setValidateForm] = useState({
    affordance_id: '',
    validation_result: 'true',
    notes: '',
  });

  // Execute form
  const [executeForm, setExecuteForm] = useState({
    affordance_id: '',
    execution_data: '',
  });

  // Rank form
  const [rankForm, setRankForm] = useState({
    metric: 'UTILITY',
    top_k: '10',
  });

  // Constraint form
  const [constraintForm, setConstraintForm] = useState({
    affordance_id: '',
    constraint_type: 'PRECONDITION',
    description: '',
    satisfied: 'true',
  });

  // Signature form
  const [signatureForm, setSignatureForm] = useState({
    affordance_id: '',
    signature_type: 'PERCEPTUAL',
    pattern: '',
    confidence: '0.5',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveAffordance.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive affordance stats');
    } finally {
      setLoading(false);
    }
  };

  const loadContexts = async () => {
    try {
      const result = await api.cognitiveAffordance.listContexts();
      const list = Array.isArray(result) ? result : (result?.contexts ?? []);
      setContexts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load contexts');
    }
  };

  const loadAffordances = async () => {
    if (!selectedContext) { setAffordances([]); return; }
    try {
      const result = await api.cognitiveAffordance.listAffordances(selectedContext);
      const list = Array.isArray(result) ? result : (result?.affordances ?? []);
      setAffordances(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load affordances');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadContexts();
    }
  }, [activeSection]);

  // Reload affordances when selected context changes
  useEffect(() => { loadAffordances(); }, [selectedContext]);

  const handleRegisterContext = async () => {
    if (!contextForm.agent_id.trim() || !contextForm.environment_id.trim()) {
      toast.error('Agent ID and Environment ID are required');
      return;
    }
    const payload: any = {
      agent_id: contextForm.agent_id.trim(),
      environment_id: contextForm.environment_id.trim(),
    };
    if (contextForm.description.trim()) payload.description = contextForm.description.trim();
    try {
      await api.cognitiveAffordance.registerContext(payload);
      toast.success('Context registered');
      setContextForm({ agent_id: '', environment_id: '', description: '' });
      await loadContexts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePerceiveAffordance = async () => {
    if (!selectedContext || !perceiveForm.name.trim()) {
      toast.error('Select a context and provide an affordance name');
      return;
    }
    const payload: any = {
      name: perceiveForm.name.trim(),
      source: perceiveForm.source,
    };
    if (perceiveForm.description.trim()) payload.description = perceiveForm.description.trim();
    if (perceiveForm.effort.trim() !== '') payload.effort = Number(perceiveForm.effort);
    if (perceiveForm.utility.trim() !== '') payload.utility = Number(perceiveForm.utility);
    if (perceiveForm.risk.trim() !== '') payload.risk = Number(perceiveForm.risk);
    try {
      await api.cognitiveAffordance.perceiveAffordance(selectedContext, payload);
      toast.success('Affordance perceived');
      setPerceiveForm({ name: '', source: 'TOOL', description: '', effort: '', utility: '', risk: '' });
      await loadAffordances();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleValidateAffordance = async () => {
    if (!validateForm.affordance_id.trim()) {
      toast.error('Affordance ID is required');
      return;
    }
    const payload: any = { validation_result: validateForm.validation_result === 'true' };
    if (validateForm.notes.trim()) payload.notes = validateForm.notes.trim();
    try {
      await api.cognitiveAffordance.validateAffordance(validateForm.affordance_id.trim(), payload);
      toast.success('Affordance validated');
      setValidateForm({ affordance_id: '', validation_result: 'true', notes: '' });
      await loadAffordances();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleExecuteAffordance = async () => {
    if (!executeForm.affordance_id.trim()) {
      toast.error('Affordance ID is required');
      return;
    }
    let execData: any = undefined;
    if (executeForm.execution_data.trim()) {
      try { execData = JSON.parse(executeForm.execution_data); }
      catch { toast.error('Execution data must be valid JSON'); return; }
    }
    try {
      await api.cognitiveAffordance.executeAffordance(executeForm.affordance_id.trim(), execData);
      toast.success('Affordance executed');
      setExecuteForm({ affordance_id: '', execution_data: '' });
      await loadAffordances();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRankAffordances = async () => {
    if (!selectedContext) { toast.error('Select a context first'); return; }
    const metric = rankForm.metric;
    const topK = rankForm.top_k.trim() !== '' ? Number(rankForm.top_k) : undefined;
    try {
      const result = await api.cognitiveAffordance.rankAffordances(selectedContext, metric, topK);
      setRankResult(result);
      toast.success('Affordances ranked');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddConstraint = async () => {
    if (!constraintForm.affordance_id.trim() || !constraintForm.description.trim()) {
      toast.error('Affordance ID and description are required');
      return;
    }
    const payload: any = {
      constraint_type: constraintForm.constraint_type,
      description: constraintForm.description.trim(),
      satisfied: constraintForm.satisfied === 'true',
    };
    try {
      await api.cognitiveAffordance.addConstraint(constraintForm.affordance_id.trim(), payload);
      toast.success('Constraint added');
      setConstraintForm({ affordance_id: '', constraint_type: 'PRECONDITION', description: '', satisfied: 'true' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddSignature = async () => {
    if (!signatureForm.affordance_id.trim() || !signatureForm.pattern.trim()) {
      toast.error('Affordance ID and pattern are required');
      return;
    }
    const payload: any = {
      signature_type: signatureForm.signature_type,
      pattern: signatureForm.pattern.trim(),
    };
    if (signatureForm.confidence.trim() !== '') payload.confidence = Number(signatureForm.confidence);
    try {
      await api.cognitiveAffordance.addSignature(signatureForm.affordance_id.trim(), payload);
      toast.success('Signature added');
      setSignatureForm({ affordance_id: '', signature_type: 'PERCEPTUAL', pattern: '', confidence: '0.5' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleBuildMap = async () => {
    if (!selectedContext) { toast.error('Select a context first'); return; }
    try {
      const result = await api.cognitiveAffordance.buildMap(selectedContext);
      setMapResult(result);
      toast.success('Affordance map built');
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
          <h2>🪏 Cognitive Affordance</h2>
          <p className="panel-subtitle">Perceive, validate, and rank action possibilities in agent contexts</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive affordance...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🪏 Cognitive Affordance</h2>
        <p className="panel-subtitle">Perceive, validate, and rank action possibilities in agent contexts</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_contexts ?? '-'}</span><span className="stat-label">Contexts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_affordances ?? '-'}</span><span className="stat-label">Affordances</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_constraints ?? '-'}</span><span className="stat-label">Constraints</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_signatures ?? '-'}</span><span className="stat-label">Signatures</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.executed_count ?? '-'}</span><span className="stat-label">Executed</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'context', 'affordance'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Cognitive Affordance Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Contexts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_contexts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Affordances</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_affordances ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Constraints</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_constraints ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Signatures</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_signatures ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Executed</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.executed_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Contexts</h3>
            <button onClick={() => loadContexts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {contexts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No contexts recorded. Register one in the Context section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {contexts.slice(0, 10).map((c: any, i: number) => {
                  const id = c.context_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[env: {c.environment_id ?? '-'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{c.description ?? ''} · {id}</div>
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
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Context</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={contextForm.agent_id} onChange={e => setContextForm({ ...contextForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Environment ID *</label>
                <input value={contextForm.environment_id} onChange={e => setContextForm({ ...contextForm, environment_id: e.target.value })} placeholder="e.g. workspace_a" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={contextForm.description} onChange={e => setContextForm({ ...contextForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleRegisterContext} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Context</button>
          </div>

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
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>env: {c.environment_id ?? '-'} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => setSelectedContext(id)}>Select</button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {selectedContext && (
              <div style={{ marginTop: 12, padding: 8, background: themeColors.accent, borderRadius: 6, color: themeColors.text, fontSize: 13 }}>
                Selected context: <strong>{selectedContext}</strong>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Affordance Section */}
      {activeSection === 'affordance' && (
        <div className="dashboard-section">
          <div style={{ padding: 12, background: themeColors.accent, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16, color: themeColors.text }}>
            Working on context: <strong>{selectedContext || 'none selected'}</strong> — choose a context in the Context section first.
          </div>

          {/* Perceive Affordance */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Perceive Affordance</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={perceiveForm.name} onChange={e => setPerceiveForm({ ...perceiveForm, name: e.target.value })} placeholder="e.g. open_file" />
              </div>
              <div className="form-group">
                <label>Source</label>
                <select value={perceiveForm.source} onChange={e => setPerceiveForm({ ...perceiveForm, source: e.target.value })}>
                  {AFFORDANCE_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={perceiveForm.description} onChange={e => setPerceiveForm({ ...perceiveForm, description: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Effort</label>
                <input value={perceiveForm.effort} onChange={e => setPerceiveForm({ ...perceiveForm, effort: e.target.value })} type="number" step="0.1" />
              </div>
              <div className="form-group">
                <label>Utility</label>
                <input value={perceiveForm.utility} onChange={e => setPerceiveForm({ ...perceiveForm, utility: e.target.value })} type="number" step="0.1" />
              </div>
              <div className="form-group">
                <label>Risk</label>
                <input value={perceiveForm.risk} onChange={e => setPerceiveForm({ ...perceiveForm, risk: e.target.value })} type="number" step="0.1" />
              </div>
            </div>
            <button onClick={handlePerceiveAffordance} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Perceive Affordance</button>
          </div>

          {/* Validate Affordance */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Validate Affordance</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Affordance ID *</label>
                <input value={validateForm.affordance_id} onChange={e => setValidateForm({ ...validateForm, affordance_id: e.target.value })} placeholder="affordance id" />
              </div>
              <div className="form-group">
                <label>Validation Result</label>
                <select value={validateForm.validation_result} onChange={e => setValidateForm({ ...validateForm, validation_result: e.target.value })}>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input value={validateForm.notes} onChange={e => setValidateForm({ ...validateForm, notes: e.target.value })} />
              </div>
            </div>
            <button onClick={handleValidateAffordance} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Validate</button>
          </div>

          {/* Execute Affordance */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Execute Affordance</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Affordance ID *</label>
                <input value={executeForm.affordance_id} onChange={e => setExecuteForm({ ...executeForm, affordance_id: e.target.value })} placeholder="affordance id" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Execution Data (JSON)</label>
                <input value={executeForm.execution_data} onChange={e => setExecuteForm({ ...executeForm, execution_data: e.target.value })} placeholder='{"args": []}' />
              </div>
            </div>
            <button onClick={handleExecuteAffordance} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Execute</button>
          </div>

          {/* Rank Affordances */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Rank Affordances</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Metric</label>
                <select value={rankForm.metric} onChange={e => setRankForm({ ...rankForm, metric: e.target.value })}>
                  {RANKING_METRICS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Top K</label>
                <input value={rankForm.top_k} onChange={e => setRankForm({ ...rankForm, top_k: e.target.value })} type="number" min="1" />
              </div>
            </div>
            <button onClick={handleRankAffordances} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Rank</button>
            {rankResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(rankResult, null, 2)}</pre>
            )}
          </div>

          {/* Add Constraint */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Constraint</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Affordance ID *</label>
                <input value={constraintForm.affordance_id} onChange={e => setConstraintForm({ ...constraintForm, affordance_id: e.target.value })} placeholder="affordance id" />
              </div>
              <div className="form-group">
                <label>Constraint Type</label>
                <select value={constraintForm.constraint_type} onChange={e => setConstraintForm({ ...constraintForm, constraint_type: e.target.value })}>
                  {CONSTRAINT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description *</label>
                <input value={constraintForm.description} onChange={e => setConstraintForm({ ...constraintForm, description: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Satisfied</label>
                <select value={constraintForm.satisfied} onChange={e => setConstraintForm({ ...constraintForm, satisfied: e.target.value })}>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              </div>
            </div>
            <button onClick={handleAddConstraint} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Constraint</button>
          </div>

          {/* Add Signature */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Signature</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Affordance ID *</label>
                <input value={signatureForm.affordance_id} onChange={e => setSignatureForm({ ...signatureForm, affordance_id: e.target.value })} placeholder="affordance id" />
              </div>
              <div className="form-group">
                <label>Signature Type</label>
                <select value={signatureForm.signature_type} onChange={e => setSignatureForm({ ...signatureForm, signature_type: e.target.value })}>
                  {SIGNATURE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Pattern *</label>
                <input value={signatureForm.pattern} onChange={e => setSignatureForm({ ...signatureForm, pattern: e.target.value })} placeholder="e.g. button_clickable" />
              </div>
              <div className="form-group">
                <label>Confidence</label>
                <input value={signatureForm.confidence} onChange={e => setSignatureForm({ ...signatureForm, confidence: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
            </div>
            <button onClick={handleAddSignature} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Signature</button>
          </div>

          {/* Build Map */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Build Affordance Map</h3>
            <button onClick={handleBuildMap} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Build Map</button>
            {mapResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 200, fontSize: 11 }}>{JSON.stringify(mapResult, null, 2)}</pre>
            )}
          </div>

          {/* Affordances List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Affordances ({affordances.length})</h3>
            <button onClick={() => loadAffordances()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {affordances.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No affordances recorded for the selected context.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {affordances.slice(0, 30).map((a: any, i: number) => {
                  const id = a.affordance_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{a.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.source && renderBadge(a.source, themeColors.secondary)}
                          {a.status && renderBadge(a.status, statusColor(a.status))}
                        </div>
                      </div>
                      {a.description && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.8, marginTop: 6 }}>{a.description}</div>
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

export default CognitiveAffordancePanel;
