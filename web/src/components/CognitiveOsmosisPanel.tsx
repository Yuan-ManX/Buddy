import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: teal for cognitive osmosis
const themeColors = {
  primary: '#0d9488',
  secondary: '#14b8a6',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#134e4a',
};

// Enum values must match backend MembraneType / PermeabilityLevel / AbsorptionOutcome / OsmoticRegime / EqualizationState exactly (uppercase).
const MEMBRANE_TYPES = ['CONCEPTUAL', 'EMOTIONAL', 'EPISTEMIC', 'CULTURAL', 'LOGICAL', 'AESTHETIC'];
const PERMEABILITY_LEVELS = ['IMPERMEABLE', 'LOW', 'MODERATE', 'HIGH', 'FULLY_PERMEABLE'];
const ABSORPTION_OUTCOMES = ['ABSORBED', 'PARTIAL', 'FILTERED', 'REJECTED', 'TRANSFORMED'];
const OSMOTIC_REGIMES = ['ISOLATED', 'TRICKLE', 'BALANCED', 'SATURATED', 'LEAKING'];
const EQUALIZATION_STATES = ['DEFICIT', 'SURPLUS', 'EQUILIBRIUM', 'FLUCTUATING', 'REVERSING'];

// Map an osmotic regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  ISOLATED: '#9ca3af',
  TRICKLE: '#f97316',
  BALANCED: '#0d9488',
  SATURATED: '#0ea5e9',
  LEAKING: '#dc2626',
};

export const CognitiveOsmosisPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'absorption' | 'membrane' | 'regulation'>('overview');

  // Absorptions / readings / plans
  const [absorptions, setAbsorptions] = useState<any[]>([]);
  const [readings, setReadings] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record absorption form
  const [absorptionForm, setAbsorptionForm] = useState({
    agent_id: '',
    membrane: 'CONCEPTUAL',
    concept: '',
    permeability: 'MODERATE',
    outcome: 'ABSORBED',
    concentration_before: '',
    concentration_after: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Read membrane form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    membrane: 'CONCEPTUAL',
    permeability: 'MODERATE',
    selectivity_score: '',
  });

  // Record gradient form
  const [gradientForm, setGradientForm] = useState({
    agent_id: '',
    membrane: 'CONCEPTUAL',
    state: 'EQUILIBRIUM',
    internal_concentration: '',
    external_concentration: '',
  });

  // Plan regulation form
  const [regulationForm, setRegulationForm] = useState({
    agent_id: '',
    membrane: 'CONCEPTUAL',
    target_permeability: 'MODERATE',
    rationale: '',
    expected_effect: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveOsmosis.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive osmosis stats');
    } finally {
      setLoading(false);
    }
  };

  const loadAbsorptions = async () => {
    try {
      const result = await api.cognitiveOsmosis.listAbsorptions();
      const list = Array.isArray(result) ? result : (result?.absorptions ?? []);
      setAbsorptions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load absorptions');
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveOsmosis.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveOsmosis.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadAbsorptions();
      loadReadings();
      loadPlans();
    }
  }, [activeSection]);

  const handleRecordAbsorption = async () => {
    if (!absorptionForm.agent_id.trim() || !absorptionForm.concept.trim()) {
      toast.error('Agent ID and concept are required');
      return;
    }
    const payload: any = {
      agent_id: absorptionForm.agent_id.trim(),
      membrane: absorptionForm.membrane,
      concept: absorptionForm.concept.trim(),
      permeability: absorptionForm.permeability,
      outcome: absorptionForm.outcome,
      concentration_before: Number(absorptionForm.concentration_before),
      concentration_after: Number(absorptionForm.concentration_after),
    };
    try {
      await api.cognitiveOsmosis.recordAbsorption(payload);
      toast.success('Absorption recorded');
      setAbsorptionForm({ agent_id: '', membrane: 'CONCEPTUAL', concept: '', permeability: 'MODERATE', outcome: 'ABSORBED', concentration_before: '', concentration_after: '' });
      await loadAbsorptions();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveOsmosis.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleReadMembrane = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      membrane: readingForm.membrane,
      permeability: readingForm.permeability,
      selectivity_score: Number(readingForm.selectivity_score),
    };
    try {
      await api.cognitiveOsmosis.readMembrane(payload);
      toast.success('Membrane reading recorded');
      setReadingForm({ agent_id: '', membrane: 'CONCEPTUAL', permeability: 'MODERATE', selectivity_score: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordGradient = async () => {
    if (!gradientForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: gradientForm.agent_id.trim(),
      membrane: gradientForm.membrane,
      state: gradientForm.state,
      internal_concentration: Number(gradientForm.internal_concentration),
      external_concentration: Number(gradientForm.external_concentration),
    };
    try {
      await api.cognitiveOsmosis.recordGradient(payload);
      toast.success('Gradient recorded');
      setGradientForm({ agent_id: '', membrane: 'CONCEPTUAL', state: 'EQUILIBRIUM', internal_concentration: '', external_concentration: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanRegulation = async () => {
    if (!regulationForm.agent_id.trim() || !regulationForm.rationale.trim()) {
      toast.error('Agent ID and rationale are required');
      return;
    }
    const payload: any = {
      agent_id: regulationForm.agent_id.trim(),
      membrane: regulationForm.membrane,
      target_permeability: regulationForm.target_permeability,
      rationale: regulationForm.rationale.trim(),
      expected_effect: Number(regulationForm.expected_effect),
    };
    try {
      await api.cognitiveOsmosis.planRegulation(payload);
      toast.success('Regulation planned');
      setRegulationForm({ agent_id: '', membrane: 'CONCEPTUAL', target_permeability: 'MODERATE', rationale: '', expected_effect: '' });
      await loadPlans();
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
          <h2>🧬 Cognitive Osmosis</h2>
          <p className="panel-subtitle">Record absorption events, read membrane permeability, and plan regulation across cognitive membranes</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive osmosis...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧬 Cognitive Osmosis</h2>
        <p className="panel-subtitle">Record absorption events, read membrane permeability, and plan regulation across cognitive membranes</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_absorptions ?? '-'}</span><span className="stat-label">Absorptions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_plans ?? '-'}</span><span className="stat-label">Plans</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_gradients ?? '-'}</span><span className="stat-label">Gradients</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_selectivity ?? '-'}</span><span className="stat-label">Avg Selectivity</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'absorption', 'membrane', 'regulation'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Osmosis Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Absorptions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_absorptions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Readings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_readings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Plans</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_plans ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Gradients</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_gradients ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Selectivity</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_selectivity ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Absorptions</h3>
            <button onClick={() => loadAbsorptions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {absorptions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No absorptions recorded. Record one in the Absorption section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {absorptions.slice(0, 10).map((a: any, i: number) => {
                  const id = a.event_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>absorption {id}{a.concept ? ` · ${a.concept}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.membrane && renderBadge(a.membrane, themeColors.secondary)}
                          {a.outcome && renderBadge(a.outcome, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Readings</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Read one in the Membrane section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.selectivity_score != null ? ` · selectivity: ${r.selectivity_score}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.membrane && renderBadge(r.membrane, themeColors.secondary)}
                          {r.permeability && renderBadge(r.permeability, statusColor(r.permeability))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Plans</h3>
            <button onClick={() => loadPlans()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {plans.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No plans recorded. Plan one in the Regulation section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {plans.slice(0, 10).map((p: any, i: number) => {
                  const id = p.plan_id ?? p.regulation_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>plan {id}{p.rationale ? ` · ${p.rationale}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.membrane && renderBadge(p.membrane, themeColors.secondary)}
                          {p.target_permeability && renderBadge(p.target_permeability, themeColors.primary)}
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

      {/* Absorption Section */}
      {activeSection === 'absorption' && (
        <div className="dashboard-section">
          {/* Record Absorption */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Absorption</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={absorptionForm.agent_id} onChange={e => setAbsorptionForm({ ...absorptionForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Membrane</label>
                <select value={absorptionForm.membrane} onChange={e => setAbsorptionForm({ ...absorptionForm, membrane: e.target.value })}>
                  {MEMBRANE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Permeability</label>
                <select value={absorptionForm.permeability} onChange={e => setAbsorptionForm({ ...absorptionForm, permeability: e.target.value })}>
                  {PERMEABILITY_LEVELS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Outcome</label>
                <select value={absorptionForm.outcome} onChange={e => setAbsorptionForm({ ...absorptionForm, outcome: e.target.value })}>
                  {ABSORPTION_OUTCOMES.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Concept *</label>
                <input value={absorptionForm.concept} onChange={e => setAbsorptionForm({ ...absorptionForm, concept: e.target.value })} placeholder="e.g. pattern recognition" />
              </div>
              <div className="form-group">
                <label>Concentration Before</label>
                <input value={absorptionForm.concentration_before} onChange={e => setAbsorptionForm({ ...absorptionForm, concentration_before: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.2" />
              </div>
              <div className="form-group">
                <label>Concentration After</label>
                <input value={absorptionForm.concentration_after} onChange={e => setAbsorptionForm({ ...absorptionForm, concentration_after: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.8" />
              </div>
            </div>
            <button onClick={handleRecordAbsorption} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Absorption</button>
          </div>

          {/* Take Snapshot */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Take Snapshot</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={snapshotForm.agent_id} onChange={e => setSnapshotForm({ ...snapshotForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
            </div>
            <button onClick={handleTakeSnapshot} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Take Snapshot</button>
            {snapshotResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(snapshotResult, null, 2)}</pre>
            )}
          </div>

          {/* Absorptions List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Absorptions ({absorptions.length})</h3>
            <button onClick={() => loadAbsorptions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {absorptions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No absorptions recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {absorptions.slice(0, 30).map((a: any, i: number) => {
                  const id = a.event_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>absorption {id}{a.concept ? ` · ${a.concept}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.membrane && renderBadge(a.membrane, themeColors.secondary)}
                          {a.outcome && renderBadge(a.outcome, themeColors.primary)}
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

      {/* Membrane Section */}
      {activeSection === 'membrane' && (
        <div className="dashboard-section">
          {/* Read Membrane */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Read Membrane</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Membrane</label>
                <select value={readingForm.membrane} onChange={e => setReadingForm({ ...readingForm, membrane: e.target.value })}>
                  {MEMBRANE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Permeability</label>
                <select value={readingForm.permeability} onChange={e => setReadingForm({ ...readingForm, permeability: e.target.value })}>
                  {PERMEABILITY_LEVELS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Selectivity Score</label>
                <input value={readingForm.selectivity_score} onChange={e => setReadingForm({ ...readingForm, selectivity_score: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.75" />
              </div>
            </div>
            <button onClick={handleReadMembrane} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Read Membrane</button>
          </div>

          {/* Record Gradient */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Gradient</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={gradientForm.agent_id} onChange={e => setGradientForm({ ...gradientForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Membrane</label>
                <select value={gradientForm.membrane} onChange={e => setGradientForm({ ...gradientForm, membrane: e.target.value })}>
                  {MEMBRANE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Equalization State</label>
                <select value={gradientForm.state} onChange={e => setGradientForm({ ...gradientForm, state: e.target.value })}>
                  {EQUALIZATION_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Internal Concentration</label>
                <input value={gradientForm.internal_concentration} onChange={e => setGradientForm({ ...gradientForm, internal_concentration: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>External Concentration</label>
                <input value={gradientForm.external_concentration} onChange={e => setGradientForm({ ...gradientForm, external_concentration: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.9" />
              </div>
            </div>
            <button onClick={handleRecordGradient} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Gradient</button>
          </div>

          {/* Readings List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Readings ({readings.length})</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Read one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 30).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.selectivity_score != null ? ` · selectivity: ${r.selectivity_score}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.membrane && renderBadge(r.membrane, themeColors.secondary)}
                          {r.permeability && renderBadge(r.permeability, statusColor(r.permeability))}
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

      {/* Regulation Section */}
      {activeSection === 'regulation' && (
        <div className="dashboard-section">
          {/* Plan Regulation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Regulation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={regulationForm.agent_id} onChange={e => setRegulationForm({ ...regulationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Membrane</label>
                <select value={regulationForm.membrane} onChange={e => setRegulationForm({ ...regulationForm, membrane: e.target.value })}>
                  {MEMBRANE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Permeability</label>
                <select value={regulationForm.target_permeability} onChange={e => setRegulationForm({ ...regulationForm, target_permeability: e.target.value })}>
                  {PERMEABILITY_LEVELS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Effect</label>
                <input value={regulationForm.expected_effect} onChange={e => setRegulationForm({ ...regulationForm, expected_effect: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale *</label>
                <input value={regulationForm.rationale} onChange={e => setRegulationForm({ ...regulationForm, rationale: e.target.value })} placeholder="e.g. reduce noise from emotional membrane" />
              </div>
            </div>
            <button onClick={handlePlanRegulation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Regulation</button>
          </div>

          {/* Plans List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Plans ({plans.length})</h3>
            <button onClick={() => loadPlans()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {plans.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No plans recorded. Plan one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {plans.slice(0, 30).map((p: any, i: number) => {
                  const id = p.plan_id ?? p.regulation_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>plan {id}{p.rationale ? ` · ${p.rationale}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.membrane && renderBadge(p.membrane, themeColors.secondary)}
                          {p.target_permeability && renderBadge(p.target_permeability, statusColor(p.target_permeability))}
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

export default CognitiveOsmosisPanel;
