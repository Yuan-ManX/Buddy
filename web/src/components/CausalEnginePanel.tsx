import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: green/emerald for causal reasoning
const themeColors = {
  primary: '#10b981',
  secondary: '#34d399',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

// Enum values must match backend VariableType / CausalRelation /
// EvidenceStrength / InterventionStatus exactly (lowercase).
const VARIABLE_TYPES = ['treatment', 'outcome', 'confounder', 'mediator', 'collider', 'instrument', 'observed'];
const RELATIONS = ['causes', 'inhibits', 'correlates', 'confounds', 'mediates', 'moderates'];
const EVIDENCE_LEVELS = ['hypothetical', 'correlational', 'quasi_experimental', 'experimental', 'established'];
const INTERVENTION_STATUSES = ['proposed', 'active', 'completed', 'failed', 'rolled_back'];

export const CausalEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'graph' | 'variable' | 'intervention'>('overview');

  // Graphs / variables / edges
  const [graphs, setGraphs] = useState<any[]>([]);
  const [selectedGraphId, setSelectedGraphId] = useState<string>('');
  const [variables, setVariables] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [confounders, setConfounders] = useState<any>(null);

  // Selected variable & inspection
  const [selectedVariableId, setSelectedVariableId] = useState<string>('');
  const [causes, setCauses] = useState<any>(null);
  const [effects, setEffects] = useState<any>(null);
  const [path, setPath] = useState<any>(null);

  // Graph form
  const [graphForm, setGraphForm] = useState({ name: '', description: '' });

  // Variable form
  const [variableForm, setVariableForm] = useState({
    name: '',
    description: '',
    variable_type: 'observed',
    domain: '',
    current_value: '',
    observable: true,
  });

  // Edge form
  const [edgeForm, setEdgeForm] = useState({
    source_id: '',
    target_id: '',
    relation: 'causes',
    strength: '0.5',
    evidence: 'hypothetical',
    description: '',
    confidence: '0.5',
  });

  // Path query form
  const [pathForm, setPathForm] = useState({ source_id: '', target_id: '' });

  // Intervention form
  const [interventionForm, setInterventionForm] = useState({
    variable_id: '',
    target_value: '',
    rationale: '',
    expected_effect: '',
  });
  const [interventions, setInterventions] = useState<any[]>([]);
  const [interventionEffect, setInterventionEffect] = useState<any>(null);

  // Counterfactual form
  const [cfForm, setCfForm] = useState({
    premise: '',
    intervention_variable_id: '',
    observed_value: '',
    hypothesized_value: '',
    observed_outcome: '',
    estimated_outcome: '',
  });
  const [counterfactuals, setCounterfactuals] = useState<any[]>([]);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.causalEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load causal engine stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadGraphs = useCallback(async () => {
    try {
      const result = await api.causalEngine.listGraphs();
      const list = Array.isArray(result) ? result : (result?.graphs ?? []);
      setGraphs(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load graphs');
    }
  }, [toast]);

  const loadVariables = useCallback(async (graphId: string) => {
    if (!graphId) return;
    try {
      const result = await api.causalEngine.listVariables(graphId);
      const list = Array.isArray(result) ? result : (result?.variables ?? []);
      setVariables(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load variables');
    }
  }, [toast]);

  const loadEdges = useCallback(async (graphId: string) => {
    if (!graphId) return;
    try {
      const result = await api.causalEngine.listEdges(graphId);
      const list = Array.isArray(result) ? result : (result?.edges ?? []);
      setEdges(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load edges');
    }
  }, [toast]);

  const loadInterventions = useCallback(async (graphId?: string) => {
    try {
      const result = await api.causalEngine.listInterventions(graphId ? { graph_id: graphId } : undefined);
      const list = Array.isArray(result) ? result : (result?.interventions ?? []);
      setInterventions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load interventions');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + graphs when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadGraphs();
    }
  }, [activeSection, loadStats, loadGraphs]);

  // When graph changes, refresh its variables / edges
  useEffect(() => {
    if (selectedGraphId) {
      loadVariables(selectedGraphId);
      loadEdges(selectedGraphId);
      loadInterventions(selectedGraphId);
    }
  }, [selectedGraphId, loadVariables, loadEdges, loadInterventions]);

  // When entering graph section without a selection, default to first graph
  useEffect(() => {
    if (activeSection !== 'overview' && !selectedGraphId && graphs.length > 0) {
      setSelectedGraphId(graphs[0].graph_id ?? graphs[0].id);
    }
  }, [activeSection, selectedGraphId, graphs]);

  const handleCreateGraph = async () => {
    if (!graphForm.name.trim()) {
      toast.error('Graph name is required');
      return;
    }
    try {
      const result = await api.causalEngine.createGraph({
        name: graphForm.name.trim(),
        description: graphForm.description.trim() || undefined,
      });
      const newId = result?.graph_id ?? result?.id;
      toast.success(`Graph created: ${newId ?? ''}`);
      setGraphForm({ name: '', description: '' });
      await loadGraphs();
      if (newId) setSelectedGraphId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddVariable = async () => {
    if (!selectedGraphId || !variableForm.name.trim()) {
      toast.error('Graph and variable name are required');
      return;
    }
    try {
      let currentValue: any = variableForm.current_value;
      if (currentValue.trim() !== '' && !isNaN(Number(currentValue))) currentValue = Number(currentValue);
      else if (currentValue.trim() === '') currentValue = null;
      else { try { currentValue = JSON.parse(currentValue); } catch { /* keep as string */ } }
      await api.causalEngine.addVariable(selectedGraphId, {
        name: variableForm.name.trim(),
        description: variableForm.description.trim() || undefined,
        variable_type: variableForm.variable_type,
        domain: variableForm.domain.trim() || undefined,
        current_value: currentValue,
        observable: variableForm.observable,
      });
      toast.success('Variable added');
      setVariableForm({ name: '', description: '', variable_type: 'observed', domain: '', current_value: '', observable: true });
      loadVariables(selectedGraphId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEdge = async () => {
    if (!selectedGraphId || !edgeForm.source_id || !edgeForm.target_id) {
      toast.error('Source and target variables required');
      return;
    }
    try {
      await api.causalEngine.addEdge(selectedGraphId, {
        source_id: edgeForm.source_id,
        target_id: edgeForm.target_id,
        relation: edgeForm.relation,
        strength: Number(edgeForm.strength),
        evidence: edgeForm.evidence,
        description: edgeForm.description.trim() || undefined,
        confidence: Number(edgeForm.confidence),
      });
      toast.success('Edge added');
      setEdgeForm({ source_id: '', target_id: '', relation: 'causes', strength: '0.5', evidence: 'hypothetical', description: '', confidence: '0.5' });
      loadEdges(selectedGraphId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeleteEdge = async (edgeId: string) => {
    if (!selectedGraphId) return;
    try {
      await api.causalEngine.removeEdge(selectedGraphId, edgeId);
      toast.success('Edge removed');
      loadEdges(selectedGraphId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFindConfounders = async () => {
    if (!selectedGraphId) return;
    try {
      const result = await api.causalEngine.findConfounders(selectedGraphId);
      setConfounders(result);
      toast.success('Confounder analysis complete');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleInspectVariable = async (variableId: string) => {
    if (!selectedGraphId || !variableId) return;
    setSelectedVariableId(variableId);
    try {
      const c = await api.causalEngine.getCauses(selectedGraphId, variableId);
      setCauses(c);
      const e = await api.causalEngine.getEffects(selectedGraphId, variableId);
      setEffects(e);
    } catch (err: any) { toast.error(err.message); }
  };

  const handleFindPath = async () => {
    if (!selectedGraphId || !pathForm.source_id || !pathForm.target_id) return;
    try {
      const result = await api.causalEngine.getPath(selectedGraphId, pathForm.source_id, pathForm.target_id);
      setPath(result);
      toast.success('Path computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleProposeIntervention = async () => {
    if (!selectedGraphId || !interventionForm.variable_id) {
      toast.error('Variable is required for intervention');
      return;
    }
    try {
      let targetValue: any = interventionForm.target_value;
      if (targetValue.trim() !== '' && !isNaN(Number(targetValue))) targetValue = Number(targetValue);
      else { try { targetValue = JSON.parse(targetValue); } catch { /* keep as string */ } }
      let expectedEffect: any = {};
      if (interventionForm.expected_effect.trim()) {
        try { expectedEffect = JSON.parse(interventionForm.expected_effect); } catch { expectedEffect = { text: interventionForm.expected_effect }; }
      }
      const result = await api.causalEngine.proposeIntervention(selectedGraphId, {
        variable_id: interventionForm.variable_id,
        target_value: targetValue,
        rationale: interventionForm.rationale.trim() || undefined,
        expected_effect: expectedEffect,
      });
      const newId = result?.intervention_id ?? result?.id;
      toast.success(`Intervention proposed: ${newId ?? ''}`);
      setInterventionForm({ variable_id: '', target_value: '', rationale: '', expected_effect: '' });
      loadInterventions(selectedGraphId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleEstimateEffect = async (interventionId: string) => {
    try {
      const result = await api.causalEngine.estimateEffect(interventionId);
      setInterventionEffect(result);
      toast.success('Effect estimated');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleUpdateIntervention = async (interventionId: string, status: string) => {
    try {
      await api.causalEngine.updateIntervention(interventionId, { status });
      toast.success(`Intervention ${status}`);
      if (selectedGraphId) loadInterventions(selectedGraphId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateCounterfactual = async () => {
    if (!selectedGraphId) return;
    try {
      let obsVal: any = cfForm.observed_value;
      let hypVal: any = cfForm.hypothesized_value;
      if (obsVal.trim() !== '' && !isNaN(Number(obsVal))) obsVal = Number(obsVal);
      if (hypVal.trim() !== '' && !isNaN(Number(hypVal))) hypVal = Number(hypVal);
      let obsOutcome: any = {};
      let estOutcome: any = null;
      try { obsOutcome = cfForm.observed_outcome.trim() ? JSON.parse(cfForm.observed_outcome) : {}; } catch { obsOutcome = { text: cfForm.observed_outcome }; }
      if (cfForm.estimated_outcome.trim()) {
        try { estOutcome = JSON.parse(cfForm.estimated_outcome); } catch { estOutcome = { text: cfForm.estimated_outcome }; }
      }
      await api.causalEngine.createCounterfactual(selectedGraphId, {
        premise: cfForm.premise.trim(),
        intervention_variable_id: cfForm.intervention_variable_id,
        observed_value: obsVal,
        hypothesized_value: hypVal,
        observed_outcome: obsOutcome,
        estimated_outcome: estOutcome ?? undefined,
      });
      toast.success('Counterfactual created');
      setCfForm({ premise: '', intervention_variable_id: '', observed_value: '', hypothesized_value: '', observed_outcome: '', estimated_outcome: '' });
      const result = await api.causalEngine.listCounterfactuals(selectedGraphId);
      const list = Array.isArray(result) ? result : (result?.counterfactuals ?? []);
      setCounterfactuals(list);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔗 Causal Engine</h2>
          <p className="panel-subtitle">Causal graphs, do-interventions, and counterfactual analysis</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading causal engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔗 Causal Engine</h2>
        <p className="panel-subtitle">Causal graphs, do-interventions, and counterfactual analysis</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_graphs ?? '-'}</span><span className="stat-label">Graphs</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_variables ?? '-'}</span><span className="stat-label">Variables</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_edges ?? '-'}</span><span className="stat-label">Edges</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_interventions ?? '-'}</span><span className="stat-label">Interventions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_counterfactuals ?? '-'}</span><span className="stat-label">Counterfactuals</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'graph', 'variable', 'intervention'] as const).map(s => (
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

      {/* Graph selector shared across non-overview sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Graph</label>
          <select
            value={selectedGraphId}
            onChange={e => { setSelectedGraphId(e.target.value); setSelectedVariableId(''); setCauses(null); setEffects(null); setPath(null); setConfounders(null); }}
          >
            <option value="">— Select a graph —</option>
            {graphs.map((g: any) => {
              const id = g.graph_id ?? g.id;
              return <option key={id} value={id}>{g.name ?? id}</option>;
            })}
          </select>
        </div>
      )}

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Causal Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Graphs</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_graphs ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Variables</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_variables ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Edges</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_edges ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Interventions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_interventions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Counterfactuals</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_counterfactuals ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Detected Confounders</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_confounders ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Causal Graphs</h3>
            <button onClick={loadGraphs} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {graphs.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No graphs yet. Create one in the Graph section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {graphs.map((g: any) => {
                  const id = g.graph_id ?? g.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{g.name}</div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id} · {g.variable_count ?? 0} vars · {g.edge_count ?? 0} edges</div>
                      </div>
                      <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setSelectedGraphId(id); setActiveSection('variable'); }}>Open</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Graph Section */}
      {activeSection === 'graph' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Causal Graph</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={graphForm.name} onChange={e => setGraphForm({ ...graphForm, name: e.target.value })} placeholder="e.g. user_retention" />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input value={graphForm.description} onChange={e => setGraphForm({ ...graphForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreateGraph} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Graph</button>
          </div>

          {selectedGraphId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ color: themeColors.text }}>Edges ({edges.length})</h3>
                  <button onClick={handleFindConfounders} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Find Confounders</button>
                </div>
                {edges.length === 0 ? (
                  <div style={{ color: themeColors.text, opacity: 0.7, marginTop: 8 }}>No edges yet. Add them in the Variable section.</div>
                ) : (
                  <div style={{ display: 'grid', gap: 6, marginTop: 12 }}>
                    {edges.map((e: any) => {
                      const id = e.edge_id ?? e.id;
                      return (
                        <div key={id} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <span style={{ fontWeight: 600, color: themeColors.text }}>{e.source_id}</span>
                            <span style={{ color: themeColors.primary, margin: '0 8px' }}>—{e.relation}→</span>
                            <span style={{ fontWeight: 600, color: themeColors.text }}>{e.target_id}</span>
                            <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>strength {e.strength} · evidence {e.evidence} · conf {e.confidence}</div>
                          </div>
                          <button className="btn-sm" style={{ background: '#ef4444', color: '#fff' }} onClick={() => handleDeleteEdge(id)}>Delete</button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {confounders && (
                <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                  <h3 style={{ color: themeColors.text }}>Confounder Report</h3>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(confounders, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Variable Section */}
      {activeSection === 'variable' && selectedGraphId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Variable</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={variableForm.name} onChange={e => setVariableForm({ ...variableForm, name: e.target.value })} placeholder="e.g. ad_spend" />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={variableForm.variable_type} onChange={e => setVariableForm({ ...variableForm, variable_type: e.target.value })}>
                  {VARIABLE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Domain</label>
                <input value={variableForm.domain} onChange={e => setVariableForm({ ...variableForm, domain: e.target.value })} placeholder="e.g. [0, ∞)" />
              </div>
              <div className="form-group">
                <label>Current Value</label>
                <input value={variableForm.current_value} onChange={e => setVariableForm({ ...variableForm, current_value: e.target.value })} placeholder="any JSON" />
              </div>
              <div className="form-group">
                <label>Observable</label>
                <select value={variableForm.observable ? 'true' : 'false'} onChange={e => setVariableForm({ ...variableForm, observable: e.target.value === 'true' })}>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={variableForm.description} onChange={e => setVariableForm({ ...variableForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleAddVariable} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Variable</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Variables ({variables.length})</h3>
            <div style={{ display: 'grid', gap: 6, marginTop: 12 }}>
              {variables.map((v: any) => {
                const id = v.variable_id ?? v.id;
                return (
                  <div key={id} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{v.name} <span style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>· {v.variable_type}</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id} · value: {String(v.current_value ?? '-')}</div>
                    </div>
                    <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => handleInspectVariable(id)}>Inspect</button>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Causal Edge</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Source Variable *</label>
                <select value={edgeForm.source_id} onChange={e => setEdgeForm({ ...edgeForm, source_id: e.target.value })}>
                  <option value="">— select —</option>
                  {variables.map((v: any) => {
                    const id = v.variable_id ?? v.id;
                    return <option key={id} value={id}>{v.name}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Target Variable *</label>
                <select value={edgeForm.target_id} onChange={e => setEdgeForm({ ...edgeForm, target_id: e.target.value })}>
                  <option value="">— select —</option>
                  {variables.map((v: any) => {
                    const id = v.variable_id ?? v.id;
                    return <option key={id} value={id}>{v.name}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Relation</label>
                <select value={edgeForm.relation} onChange={e => setEdgeForm({ ...edgeForm, relation: e.target.value })}>
                  {RELATIONS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strength (0-1)</label>
                <input value={edgeForm.strength} onChange={e => setEdgeForm({ ...edgeForm, strength: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
              <div className="form-group">
                <label>Evidence</label>
                <select value={edgeForm.evidence} onChange={e => setEdgeForm({ ...edgeForm, evidence: e.target.value })}>
                  {EVIDENCE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Confidence (0-1)</label>
                <input value={edgeForm.confidence} onChange={e => setEdgeForm({ ...edgeForm, confidence: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={edgeForm.description} onChange={e => setEdgeForm({ ...edgeForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleAddEdge} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Edge</button>
          </div>

          {selectedVariableId && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Variable Inspection: {selectedVariableId}</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
                <div>
                  <h4 style={{ color: themeColors.text }}>Direct Causes</h4>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(causes, null, 2)}</pre>
                </div>
                <div>
                  <h4 style={{ color: themeColors.text }}>Direct Effects</h4>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(effects, null, 2)}</pre>
                </div>
              </div>
              <div style={{ marginTop: 16 }}>
                <h4 style={{ color: themeColors.text }}>Find Causal Path</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, marginTop: 8, alignItems: 'flex-end' }}>
                  <div className="form-group">
                    <label>From</label>
                    <select value={pathForm.source_id} onChange={e => setPathForm({ ...pathForm, source_id: e.target.value })}>
                      <option value="">— select —</option>
                      {variables.map((v: any) => {
                        const id = v.variable_id ?? v.id;
                        return <option key={id} value={id}>{v.name}</option>;
                      })}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>To</label>
                    <select value={pathForm.target_id} onChange={e => setPathForm({ ...pathForm, target_id: e.target.value })}>
                      <option value="">— select —</option>
                      {variables.map((v: any) => {
                        const id = v.variable_id ?? v.id;
                        return <option key={id} value={id}>{v.name}</option>;
                      })}
                    </select>
                  </div>
                  <button onClick={handleFindPath} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Find</button>
                </div>
                {path && (
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(path, null, 2)}</pre>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Intervention Section */}
      {activeSection === 'intervention' && selectedGraphId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Propose do-Intervention</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Variable *</label>
                <select value={interventionForm.variable_id} onChange={e => setInterventionForm({ ...interventionForm, variable_id: e.target.value })}>
                  <option value="">— select —</option>
                  {variables.map((v: any) => {
                    const id = v.variable_id ?? v.id;
                    return <option key={id} value={id}>{v.name}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Target Value *</label>
                <input value={interventionForm.target_value} onChange={e => setInterventionForm({ ...interventionForm, target_value: e.target.value })} placeholder="any JSON" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input value={interventionForm.rationale} onChange={e => setInterventionForm({ ...interventionForm, rationale: e.target.value })} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Expected Effect (JSON)</label>
                <textarea rows={3} value={interventionForm.expected_effect} onChange={e => setInterventionForm({ ...interventionForm, expected_effect: e.target.value })} placeholder='{"outcome_var": "increase"}' />
              </div>
            </div>
            <button onClick={handleProposeIntervention} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Propose Intervention</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Interventions ({interventions.length})</h3>
            <button onClick={() => loadInterventions(selectedGraphId)} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {interventions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No interventions yet.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {interventions.map((i: any) => {
                  const id = i.intervention_id ?? i.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>do({i.variable_id}) = {String(i.target_value)}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id} · status: {i.status}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => handleEstimateEffect(id)}>Estimate</button>
                          <select
                            value={i.status}
                            onChange={e => handleUpdateIntervention(id, e.target.value)}
                            style={{ padding: '4px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                          >
                            {INTERVENTION_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {interventionEffect && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Estimated Effect</h3>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(interventionEffect, null, 2)}</pre>
            </div>
          )}

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Counterfactual Analysis</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Premise *</label>
                <input value={cfForm.premise} onChange={e => setCfForm({ ...cfForm, premise: e.target.value })} placeholder="What if X had been different?" />
              </div>
              <div className="form-group">
                <label>Intervention Variable *</label>
                <select value={cfForm.intervention_variable_id} onChange={e => setCfForm({ ...cfForm, intervention_variable_id: e.target.value })}>
                  <option value="">— select —</option>
                  {variables.map((v: any) => {
                    const id = v.variable_id ?? v.id;
                    return <option key={id} value={id}>{v.name}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Observed Value</label>
                <input value={cfForm.observed_value} onChange={e => setCfForm({ ...cfForm, observed_value: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Hypothesized Value</label>
                <input value={cfForm.hypothesized_value} onChange={e => setCfForm({ ...cfForm, hypothesized_value: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Observed Outcome (JSON)</label>
                <input value={cfForm.observed_outcome} onChange={e => setCfForm({ ...cfForm, observed_outcome: e.target.value })} placeholder='{"y": 10}' />
              </div>
              <div className="form-group">
                <label>Estimated Outcome (JSON)</label>
                <input value={cfForm.estimated_outcome} onChange={e => setCfForm({ ...cfForm, estimated_outcome: e.target.value })} placeholder='optional' />
              </div>
            </div>
            <button onClick={handleCreateCounterfactual} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Counterfactual</button>
            {counterfactuals.length > 0 && (
              <div style={{ display: 'grid', gap: 8, marginTop: 16 }}>
                {counterfactuals.map((c: any, idx: number) => {
                  const id = c.counterfactual_id ?? c.id ?? idx;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{c.premise}</div>
                      <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 11, marginTop: 6 }}>{JSON.stringify(c, null, 2)}</pre>
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

export default CausalEnginePanel;
