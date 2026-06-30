import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: teal for scenario simulation
const themeColors = {
  primary: '#0d9488',
  secondary: '#14b8a6',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#134e4a',
};

// Enum values must match backend ScenarioType / VariableType / Distribution exactly (lowercase).
const SCENARIO_TYPES = ['deterministic', 'stochastic', 'adversarial', 'monte_carlo'];
const VARIABLE_TYPES = ['continuous', 'discrete', 'categorical', 'binary'];
const DISTRIBUTIONS = ['uniform', 'normal', 'triangular', 'exponential', 'categorical'];

export const ScenarioSimulatorPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'scenario' | 'simulate'>('overview');

  // Scenarios / variables / actions / outcomes
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [scenarioDetail, setScenarioDetail] = useState<any>(null);
  const [variables, setVariables] = useState<any[]>([]);
  const [actions, setActions] = useState<any[]>([]);
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [report, setReport] = useState<any>(null);
  const [lastSimulation, setLastSimulation] = useState<any>(null);

  // Scenario form
  const [scenarioForm, setScenarioForm] = useState({
    name: '',
    description: '',
    scenario_type: 'stochastic',
    max_steps: '100',
    num_simulations: '100',
    seed: '',
  });

  // Variable form
  const [variableForm, setVariableForm] = useState({
    name: '',
    description: '',
    variable_type: 'continuous',
    distribution: 'uniform',
    min_value: '',
    max_value: '',
    mean: '',
    std: '',
    categories: '',
  });

  // Action form
  const [actionForm, setActionForm] = useState({
    name: '',
    description: '',
    preconditions: '',
    effects: '',
    probability: '1.0',
    cost: '0',
    duration: '1',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.scenarioSimulator.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load scenario simulator stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadScenarios = useCallback(async () => {
    try {
      const result = await api.scenarioSimulator.listScenarios();
      const list = Array.isArray(result) ? result : (result?.scenarios ?? []);
      setScenarios(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load scenarios');
    }
  }, [toast]);

  const loadScenarioDetail = useCallback(async (scenarioId: string) => {
    if (!scenarioId) return;
    try {
      const detail = await api.scenarioSimulator.getScenario(scenarioId);
      setScenarioDetail(detail);
      const [vars, acts] = await Promise.all([
        api.scenarioSimulator.listVariables(scenarioId).catch(() => []),
        api.scenarioSimulator.listActions(scenarioId).catch(() => []),
      ]);
      setVariables(Array.isArray(vars) ? vars : (vars?.variables ?? []));
      setActions(Array.isArray(acts) ? acts : (acts?.actions ?? []));
    } catch (e: any) {
      setScenarioDetail(null);
      setVariables([]);
      setActions([]);
    }
  }, []);

  const loadOutcomes = useCallback(async (scenarioId: string) => {
    if (!scenarioId) return;
    try {
      const result = await api.scenarioSimulator.listOutcomes(scenarioId);
      const list = Array.isArray(result) ? result : (result?.outcomes ?? []);
      setOutcomes(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load outcomes');
    }
  }, [toast]);

  const loadReport = useCallback(async (scenarioId: string) => {
    if (!scenarioId) return;
    try {
      const r = await api.scenarioSimulator.getReport(scenarioId);
      setReport(r);
    } catch (e: any) {
      // Report may not exist until a simulation has been run
      setReport(null);
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + scenarios when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadScenarios();
    }
  }, [activeSection, loadStats, loadScenarios]);

  // When scenario changes, refresh its detail, variables, actions, outcomes, report
  useEffect(() => {
    if (selectedScenarioId) {
      loadScenarioDetail(selectedScenarioId);
      loadOutcomes(selectedScenarioId);
      loadReport(selectedScenarioId);
    }
  }, [selectedScenarioId, loadScenarioDetail, loadOutcomes, loadReport]);

  // Auto-select first scenario when entering non-overview sections
  useEffect(() => {
    if (activeSection !== 'overview' && !selectedScenarioId && scenarios.length > 0) {
      setSelectedScenarioId(scenarios[0].scenario_id ?? scenarios[0].id);
    }
  }, [activeSection, selectedScenarioId, scenarios]);

  const handleCreateScenario = async () => {
    if (!scenarioForm.name.trim()) {
      toast.error('Scenario name is required');
      return;
    }
    try {
      const payload: any = {
        name: scenarioForm.name.trim(),
        description: scenarioForm.description.trim() || undefined,
        scenario_type: scenarioForm.scenario_type,
        max_steps: Number(scenarioForm.max_steps),
        num_simulations: Number(scenarioForm.num_simulations),
      };
      if (scenarioForm.seed.trim() !== '') payload.seed = Number(scenarioForm.seed);
      const result = await api.scenarioSimulator.createScenario(payload);
      toast.success('Scenario created');
      setScenarioForm({ name: '', description: '', scenario_type: 'stochastic', max_steps: '100', num_simulations: '100', seed: '' });
      await loadScenarios();
      const newId = result?.scenario_id ?? result?.id;
      if (newId) setSelectedScenarioId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddVariable = async () => {
    if (!selectedScenarioId || !variableForm.name.trim()) {
      toast.error('Scenario and variable name are required');
      return;
    }
    try {
      const payload: any = {
        name: variableForm.name.trim(),
        description: variableForm.description.trim() || undefined,
        variable_type: variableForm.variable_type,
        distribution: variableForm.distribution,
      };
      if (variableForm.min_value.trim() !== '') payload.min_value = Number(variableForm.min_value);
      if (variableForm.max_value.trim() !== '') payload.max_value = Number(variableForm.max_value);
      if (variableForm.mean.trim() !== '') payload.mean = Number(variableForm.mean);
      if (variableForm.std.trim() !== '') payload.std = Number(variableForm.std);
      if (variableForm.categories.trim() !== '') payload.categories = variableForm.categories.split(',').map(s => s.trim()).filter(Boolean);
      await api.scenarioSimulator.addVariable(selectedScenarioId, payload);
      toast.success('Variable added');
      setVariableForm({ name: '', description: '', variable_type: 'continuous', distribution: 'uniform', min_value: '', max_value: '', mean: '', std: '', categories: '' });
      loadScenarioDetail(selectedScenarioId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddAction = async () => {
    if (!selectedScenarioId || !actionForm.name.trim()) {
      toast.error('Scenario and action name are required');
      return;
    }
    try {
      const payload: any = {
        name: actionForm.name.trim(),
        description: actionForm.description.trim() || undefined,
        probability: Number(actionForm.probability),
        cost: Number(actionForm.cost),
        duration: Number(actionForm.duration),
      };
      if (actionForm.preconditions.trim()) {
        payload.preconditions = actionForm.preconditions.split(',').map(s => s.trim()).filter(Boolean);
      }
      if (actionForm.effects.trim()) {
        try { payload.effects = JSON.parse(actionForm.effects); } catch { toast.error('Effects must be valid JSON'); return; }
      }
      await api.scenarioSimulator.addAction(selectedScenarioId, payload);
      toast.success('Action added');
      setActionForm({ name: '', description: '', preconditions: '', effects: '', probability: '1.0', cost: '0', duration: '1' });
      loadScenarioDetail(selectedScenarioId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRunSimulation = async () => {
    if (!selectedScenarioId) return;
    try {
      const result = await api.scenarioSimulator.runSimulation(selectedScenarioId);
      setLastSimulation(result);
      toast.success('Simulation completed');
      loadOutcomes(selectedScenarioId);
      loadReport(selectedScenarioId);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🎲 Scenario Simulator</h2>
          <p className="panel-subtitle">Build scenarios, define variables and actions, run simulations</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading scenario simulator...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🎲 Scenario Simulator</h2>
        <p className="panel-subtitle">Build scenarios, define variables and actions, run simulations</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_scenarios ?? '-'}</span><span className="stat-label">Scenarios</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_variables ?? '-'}</span><span className="stat-label">Variables</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_actions ?? '-'}</span><span className="stat-label">Actions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_simulations ?? '-'}</span><span className="stat-label">Simulations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_outcomes ?? '-'}</span><span className="stat-label">Outcomes</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'scenario', 'simulate'] as const).map(s => (
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

      {/* Scenario selector shared across non-overview sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Scenario</label>
          <select
            value={selectedScenarioId}
            onChange={e => { setSelectedScenarioId(e.target.value); setReport(null); setLastSimulation(null); setOutcomes([]); }}
          >
            <option value="">— Select a scenario —</option>
            {scenarios.map((s: any) => {
              const id = s.scenario_id ?? s.id;
              return <option key={id} value={id}>{s.name ?? id}</option>;
            })}
          </select>
        </div>
      )}

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Scenario Simulator Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Scenarios</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_scenarios ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Variables</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_variables ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Actions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_actions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Simulations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_simulations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Outcomes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_outcomes ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Scenarios</h3>
            <button onClick={() => loadScenarios()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {scenarios.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No scenarios recorded. Create one in the Scenario section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {scenarios.slice(0, 10).map((s: any) => {
                  const id = s.scenario_id ?? s.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{s.name ?? 'unnamed'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{s.scenario_type ?? 'unknown'}]</span></div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{s.description ?? ''} · {id}</div>
                        </div>
                        <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setActiveSection('scenario'); setSelectedScenarioId(id); }}>Open</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Scenario Section */}
      {activeSection === 'scenario' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Scenario</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={scenarioForm.name} onChange={e => setScenarioForm({ ...scenarioForm, name: e.target.value })} placeholder="e.g. market_crash_2024" />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={scenarioForm.scenario_type} onChange={e => setScenarioForm({ ...scenarioForm, scenario_type: e.target.value })}>
                  {SCENARIO_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Max Steps</label>
                <input value={scenarioForm.max_steps} onChange={e => setScenarioForm({ ...scenarioForm, max_steps: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Num Simulations</label>
                <input value={scenarioForm.num_simulations} onChange={e => setScenarioForm({ ...scenarioForm, num_simulations: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Seed (optional)</label>
                <input value={scenarioForm.seed} onChange={e => setScenarioForm({ ...scenarioForm, seed: e.target.value })} type="number" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={scenarioForm.description} onChange={e => setScenarioForm({ ...scenarioForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreateScenario} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Scenario</button>
          </div>

          {selectedScenarioId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Variable</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input value={variableForm.name} onChange={e => setVariableForm({ ...variableForm, name: e.target.value })} placeholder="e.g. interest_rate" />
                  </div>
                  <div className="form-group">
                    <label>Variable Type</label>
                    <select value={variableForm.variable_type} onChange={e => setVariableForm({ ...variableForm, variable_type: e.target.value })}>
                      {VARIABLE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Distribution</label>
                    <select value={variableForm.distribution} onChange={e => setVariableForm({ ...variableForm, distribution: e.target.value })}>
                      {DISTRIBUTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Min Value</label>
                    <input value={variableForm.min_value} onChange={e => setVariableForm({ ...variableForm, min_value: e.target.value })} type="number" />
                  </div>
                  <div className="form-group">
                    <label>Max Value</label>
                    <input value={variableForm.max_value} onChange={e => setVariableForm({ ...variableForm, max_value: e.target.value })} type="number" />
                  </div>
                  <div className="form-group">
                    <label>Mean</label>
                    <input value={variableForm.mean} onChange={e => setVariableForm({ ...variableForm, mean: e.target.value })} type="number" />
                  </div>
                  <div className="form-group">
                    <label>Std</label>
                    <input value={variableForm.std} onChange={e => setVariableForm({ ...variableForm, std: e.target.value })} type="number" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Categories (comma-separated)</label>
                    <input value={variableForm.categories} onChange={e => setVariableForm({ ...variableForm, categories: e.target.value })} placeholder="low, medium, high" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={variableForm.description} onChange={e => setVariableForm({ ...variableForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddVariable} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Variable</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Action</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input value={actionForm.name} onChange={e => setActionForm({ ...actionForm, name: e.target.value })} placeholder="e.g. buy_asset" />
                  </div>
                  <div className="form-group">
                    <label>Probability</label>
                    <input value={actionForm.probability} onChange={e => setActionForm({ ...actionForm, probability: e.target.value })} type="number" min="0" max="1" step="0.1" />
                  </div>
                  <div className="form-group">
                    <label>Cost</label>
                    <input value={actionForm.cost} onChange={e => setActionForm({ ...actionForm, cost: e.target.value })} type="number" />
                  </div>
                  <div className="form-group">
                    <label>Duration</label>
                    <input value={actionForm.duration} onChange={e => setActionForm({ ...actionForm, duration: e.target.value })} type="number" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Preconditions (comma-separated)</label>
                    <input value={actionForm.preconditions} onChange={e => setActionForm({ ...actionForm, preconditions: e.target.value })} placeholder="market_open, funds_available" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Effects (JSON)</label>
                    <input value={actionForm.effects} onChange={e => setActionForm({ ...actionForm, effects: e.target.value })} placeholder='{"capital": 1.0, "risk": -0.5}' />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={actionForm.description} onChange={e => setActionForm({ ...actionForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddAction} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Action</button>
              </div>

              {scenarioDetail && (
                <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                  <h3 style={{ color: themeColors.text }}>Scenario: {selectedScenarioId}</h3>
                  <h4 style={{ color: themeColors.text, marginTop: 12 }}>Variables ({variables.length})</h4>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(variables, null, 2)}</pre>
                  <h4 style={{ color: themeColors.text, marginTop: 12 }}>Actions ({actions.length})</h4>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(actions, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Simulate Section */}
      {activeSection === 'simulate' && selectedScenarioId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Run Simulation</h3>
            <p style={{ color: themeColors.text, opacity: 0.8, marginTop: 4 }}>Run the configured scenario to generate outcomes and a report.</p>
            <button onClick={handleRunSimulation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Run Simulation</button>
          </div>

          {lastSimulation && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Last Simulation Result</h3>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(lastSimulation, null, 2)}</pre>
            </div>
          )}

          {report && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Report</h3>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(report, null, 2)}</pre>
            </div>
          )}

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Outcomes ({outcomes.length})</h3>
            <button onClick={() => loadOutcomes(selectedScenarioId)} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {outcomes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No outcomes recorded. Run a simulation to generate them.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {outcomes.slice(0, 20).map((o: any, i: number) => {
                  const id = o.outcome_id ?? o.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{o.action ?? 'step'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[step {o.step ?? i}]</span></div>
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

export default ScenarioSimulatorPanel;
