import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: blue for mental simulation
const themeColors = {
  primary: '#2563eb',
  secondary: '#3b82f6',
  bg: '#eff6ff',
  border: '#bfdbfe',
  accent: '#dbeafe',
  text: '#1e3a8a',
};

// Enum values must match backend SimulationType / SimulationStatus / ModelType / OutcomeValence / ConfidenceLevel exactly (lowercase).
const SIMULATION_TYPES = ['predictive', 'counterfactual', 'hypothetical', 'retrospective', 'exploratory'];
const SIMULATION_STATUS = ['draft', 'running', 'completed', 'failed', 'cancelled'];
const MODEL_TYPES = ['deterministic', 'probabilistic', 'heuristic', 'neural', 'hybrid'];
const OUTCOME_VALENCES = ['positive', 'negative', 'neutral', 'mixed'];
const CONFIDENCE_LEVELS = ['very_low', 'low', 'medium', 'high', 'very_high'];

const STATUS_COLORS: Record<string, string> = {
  draft: '#9ca3af',
  running: '#2563eb',
  completed: '#059669',
  failed: '#dc2626',
  cancelled: '#6b7280',
};

const VALENCE_COLORS: Record<string, string> = {
  positive: '#059669',
  negative: '#dc2626',
  neutral: '#6b7280',
  mixed: '#d97706',
};

export const MentalSimulationPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'model' | 'simulation'>('overview');

  // Models / simulations / steps / outcomes
  const [models, setModels] = useState<any[]>([]);
  const [simulations, setSimulations] = useState<any[]>([]);
  const [selectedSimulationId, setSelectedSimulationId] = useState<string>('');
  const [steps, setSteps] = useState<any[]>([]);
  const [outcomes, setOutcomes] = useState<any[]>([]);

  // Model form
  const [modelForm, setModelForm] = useState({
    name: '',
    model_type: 'probabilistic',
    description: '',
    parameters: '',
  });

  // Simulation form
  const [simulationForm, setSimulationForm] = useState({
    model_id: '',
    simulation_type: 'predictive',
    description: '',
    max_steps: '50',
  });

  // Step form
  const [stepForm, setStepForm] = useState({
    action: '',
    description: '',
    state: '',
  });

  // Outcome form
  const [outcomeForm, setOutcomeForm] = useState({
    description: '',
    valence: 'neutral',
    confidence: 'medium',
    value: '',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.mentalSimulation.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load mental simulation stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadModels = useCallback(async () => {
    try {
      const result = await api.mentalSimulation.listModels();
      const list = Array.isArray(result) ? result : (result?.models ?? []);
      setModels(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load models');
    }
  }, [toast]);

  const loadSimulations = useCallback(async () => {
    try {
      const result = await api.mentalSimulation.listSimulations();
      const list = Array.isArray(result) ? result : (result?.simulations ?? []);
      setSimulations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load simulations');
    }
  }, [toast]);

  const loadSimulationDetail = useCallback(async (simulationId: string) => {
    if (!simulationId) return;
    try {
      const [st, oc] = await Promise.all([
        api.mentalSimulation.listSteps(simulationId).catch(() => []),
        api.mentalSimulation.listOutcomes(simulationId).catch(() => []),
      ]);
      setSteps(Array.isArray(st) ? st : (st?.steps ?? []));
      setOutcomes(Array.isArray(oc) ? oc : (oc?.outcomes ?? []));
    } catch {
      setSteps([]);
      setOutcomes([]);
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadModels();
      loadSimulations();
    }
  }, [activeSection, loadStats, loadModels, loadSimulations]);

  // When the active simulation changes, refresh its steps and outcomes
  useEffect(() => {
    if (selectedSimulationId) loadSimulationDetail(selectedSimulationId);
  }, [selectedSimulationId, loadSimulationDetail]);

  // Auto-select first simulation when entering the simulation section
  useEffect(() => {
    if (activeSection === 'simulation' && !selectedSimulationId && simulations.length > 0) {
      setSelectedSimulationId(simulations[0].simulation_id ?? simulations[0].id);
    }
  }, [activeSection, selectedSimulationId, simulations]);

  const handleCreateModel = async () => {
    if (!modelForm.name.trim()) {
      toast.error('Model name is required');
      return;
    }
    let parameters: any = {};
    if (modelForm.parameters.trim() !== '') {
      try { parameters = JSON.parse(modelForm.parameters); }
      catch { toast.error('Parameters must be valid JSON'); return; }
    }
    try {
      const payload: any = {
        name: modelForm.name.trim(),
        model_type: modelForm.model_type,
        parameters,
      };
      if (modelForm.description.trim()) payload.description = modelForm.description.trim();
      await api.mentalSimulation.createModel(payload);
      toast.success('Mental model created');
      setModelForm({ name: '', model_type: 'probabilistic', description: '', parameters: '' });
      await loadModels();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeleteModel = async (modelId: string) => {
    try {
      await api.mentalSimulation.deleteModel(modelId);
      toast.success('Model deleted');
      await loadModels();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateSimulation = async () => {
    if (!simulationForm.model_id.trim()) {
      toast.error('A mental model is required');
      return;
    }
    try {
      const payload: any = {
        model_id: simulationForm.model_id.trim(),
        simulation_type: simulationForm.simulation_type,
      };
      if (simulationForm.description.trim()) payload.description = simulationForm.description.trim();
      if (simulationForm.max_steps.trim() !== '') payload.max_steps = Number(simulationForm.max_steps);
      const result = await api.mentalSimulation.createSimulation(payload);
      toast.success('Simulation created');
      setSimulationForm({ model_id: '', simulation_type: 'predictive', description: '', max_steps: '50' });
      await loadSimulations();
      const newId = result?.simulation_id ?? result?.id;
      if (newId) setSelectedSimulationId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddStep = async () => {
    if (!selectedSimulationId || !stepForm.action.trim()) {
      toast.error('Simulation and action are required');
      return;
    }
    let state: any = {};
    if (stepForm.state.trim() !== '') {
      try { state = JSON.parse(stepForm.state); }
      catch { toast.error('State must be valid JSON'); return; }
    }
    try {
      const payload: any = { action: stepForm.action.trim(), state };
      if (stepForm.description.trim()) payload.description = stepForm.description.trim();
      await api.mentalSimulation.addStep(selectedSimulationId, payload);
      toast.success('Step added');
      setStepForm({ action: '', description: '', state: '' });
      loadSimulationDetail(selectedSimulationId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordOutcome = async () => {
    if (!selectedSimulationId || !outcomeForm.description.trim()) {
      toast.error('Simulation and outcome description are required');
      return;
    }
    try {
      const payload: any = {
        description: outcomeForm.description.trim(),
        valence: outcomeForm.valence,
        confidence: outcomeForm.confidence,
      };
      if (outcomeForm.value.trim() !== '') payload.value = Number(outcomeForm.value);
      await api.mentalSimulation.recordOutcome(selectedSimulationId, payload);
      toast.success('Outcome recorded');
      setOutcomeForm({ description: '', valence: 'neutral', confidence: 'medium', value: '' });
      loadSimulationDetail(selectedSimulationId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCancelSimulation = async (simulationId: string) => {
    try {
      await api.mentalSimulation.cancelSimulation(simulationId);
      toast.success('Simulation cancelled');
      await loadSimulations();
      if (simulationId === selectedSimulationId) loadSimulationDetail(simulationId);
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
  const valenceColor = (v: string) => VALENCE_COLORS[v] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔮 Mental Simulation</h2>
          <p className="panel-subtitle">Build mental models, run simulations, and record outcomes</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading mental simulation...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔮 Mental Simulation</h2>
        <p className="panel-subtitle">Build mental models, run simulations, and record outcomes</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_models ?? '-'}</span><span className="stat-label">Models</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_simulations ?? '-'}</span><span className="stat-label">Simulations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_steps ?? '-'}</span><span className="stat-label">Steps</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_outcomes ?? '-'}</span><span className="stat-label">Outcomes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.completed_count ?? '-'}</span><span className="stat-label">Completed</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'model', 'simulation'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Mental Simulation Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Models</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_models ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Simulations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_simulations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Steps</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_steps ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Outcomes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_outcomes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Completed</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.completed_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Simulations</h3>
            <button onClick={() => loadSimulations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {simulations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No simulations recorded. Create one in the Simulation section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {simulations.slice(0, 10).map((s: any, i: number) => {
                  const id = s.simulation_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{s.simulation_type ?? 'simulation'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{s.status ?? 'unknown'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{s.description ?? ''} · {id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Model Section */}
      {activeSection === 'model' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Mental Model</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={modelForm.name} onChange={e => setModelForm({ ...modelForm, name: e.target.value })} placeholder="e.g. market_dynamics" />
              </div>
              <div className="form-group">
                <label>Model Type</label>
                <select value={modelForm.model_type} onChange={e => setModelForm({ ...modelForm, model_type: e.target.value })}>
                  {MODEL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Parameters (JSON)</label>
                <input value={modelForm.parameters} onChange={e => setModelForm({ ...modelForm, parameters: e.target.value })} placeholder='{"volatility": 0.2, "drift": 0.01}' />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={modelForm.description} onChange={e => setModelForm({ ...modelForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreateModel} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Model</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Mental Models ({models.length})</h3>
            <button onClick={() => loadModels()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {models.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No models recorded. Create one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {models.slice(0, 30).map((m: any, i: number) => {
                  const id = m.model_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{m.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{m.description ?? ''} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.model_type && renderBadge(m.model_type, themeColors.secondary)}
                          <button className="btn-sm" style={{ background: '#dc2626', color: '#fff', marginLeft: 4 }} onClick={() => handleDeleteModel(id)}>Delete</button>
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

      {/* Simulation Section */}
      {activeSection === 'simulation' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Simulation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Mental Model *</label>
                <select value={simulationForm.model_id} onChange={e => setSimulationForm({ ...simulationForm, model_id: e.target.value })}>
                  <option value="">— Select a model —</option>
                  {models.map((m: any) => {
                    const id = m.model_id ?? m.id;
                    return <option key={id} value={id}>{m.name ?? id}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Simulation Type</label>
                <select value={simulationForm.simulation_type} onChange={e => setSimulationForm({ ...simulationForm, simulation_type: e.target.value })}>
                  {SIMULATION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Max Steps</label>
                <input value={simulationForm.max_steps} onChange={e => setSimulationForm({ ...simulationForm, max_steps: e.target.value })} type="number" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={simulationForm.description} onChange={e => setSimulationForm({ ...simulationForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreateSimulation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Simulation</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Simulations ({simulations.length})</h3>
            <button onClick={() => loadSimulations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label>Active Simulation</label>
              <select
                value={selectedSimulationId}
                onChange={e => { setSelectedSimulationId(e.target.value); setSteps([]); setOutcomes([]); }}
              >
                <option value="">— Select a simulation —</option>
                {simulations.map((s: any) => {
                  const id = s.simulation_id ?? s.id;
                  return <option key={id} value={id}>{s.simulation_type ?? 'simulation'} · {id}</option>;
                })}
              </select>
            </div>
            {simulations.length === 0 && (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No simulations recorded. Create one above.</div>
            )}
            {simulations.slice(0, 20).map((s: any, i: number) => {
              const id = s.simulation_id ?? s.id ?? i;
              return (
                <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}`, marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                    <div>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{s.simulation_type ?? 'simulation'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{s.description ?? ''} · {id}</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                      {s.status && renderBadge(s.status, statusColor(s.status))}
                      <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => setSelectedSimulationId(id)}>Open</button>
                      <button className="btn-sm" style={{ background: '#dc2626', color: '#fff', marginLeft: 4 }} onClick={() => handleCancelSimulation(id)}>Cancel</button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {selectedSimulationId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Step</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Action *</label>
                    <input value={stepForm.action} onChange={e => setStepForm({ ...stepForm, action: e.target.value })} placeholder="e.g. apply_policy" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>State (JSON)</label>
                    <input value={stepForm.state} onChange={e => setStepForm({ ...stepForm, state: e.target.value })} placeholder='{"capital": 100, "risk": 0.3}' />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={stepForm.description} onChange={e => setStepForm({ ...stepForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddStep} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Step</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Record Outcome</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Valence</label>
                    <select value={outcomeForm.valence} onChange={e => setOutcomeForm({ ...outcomeForm, valence: e.target.value })}>
                      {OUTCOME_VALENCES.map(v => <option key={v} value={v}>{v}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Confidence</label>
                    <select value={outcomeForm.confidence} onChange={e => setOutcomeForm({ ...outcomeForm, confidence: e.target.value })}>
                      {CONFIDENCE_LEVELS.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Value</label>
                    <input value={outcomeForm.value} onChange={e => setOutcomeForm({ ...outcomeForm, value: e.target.value })} type="number" step="0.01" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description *</label>
                    <input value={outcomeForm.description} onChange={e => setOutcomeForm({ ...outcomeForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleRecordOutcome} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Outcome</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <h3 style={{ color: themeColors.text }}>Simulation: {selectedSimulationId}</h3>
                <h4 style={{ color: themeColors.text, marginTop: 12 }}>Steps ({steps.length})</h4>
                <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(steps, null, 2)}</pre>
                <h4 style={{ color: themeColors.text, marginTop: 12 }}>Outcomes ({outcomes.length})</h4>
                <div style={{ display: 'grid', gap: 6, marginTop: 6 }}>
                  {outcomes.length === 0 ? (
                    <div style={{ color: themeColors.text, opacity: 0.7 }}>No outcomes recorded yet.</div>
                  ) : outcomes.slice(0, 20).map((o: any, i: number) => {
                    const oid = o.outcome_id ?? o.id ?? i;
                    return (
                      <div key={oid} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
                          <span style={{ color: themeColors.text }}>{o.description ?? oid}</span>
                          <span>
                            {o.valence && renderBadge(o.valence, valenceColor(o.valence))}
                            {o.confidence && renderBadge(o.confidence, themeColors.secondary)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default MentalSimulationPanel;
