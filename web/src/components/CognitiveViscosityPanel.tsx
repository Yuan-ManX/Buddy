import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: violet for cognitive viscosity
const themeColors = {
  primary: '#7c3aed',
  secondary: '#8b5cf6',
  bg: '#f5f3ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

// Enum values must match backend FluidType / ViscosityRegime / FlowState / ThinningStrategy / ResistanceType exactly (uppercase).
const FLUID_TYPES = ['WATERLIKE', 'OILY', 'TARLIKE', 'CRYSTALLINE', 'GLASSY', 'PLASMA'];
const VISCOSITY_REGIMES = ['INVISCID', 'SUPPLE', 'STANDARD', 'STICKY', 'RIGID', 'FROZEN'];
const FLOW_STATES = ['LAMINAR', 'TRANSITIONAL', 'TURBULENT', 'STAGNANT', 'REVERSED'];
const THINNING_STRATEGIES = ['SHEAR_THIN', 'TEMPERATURE_RISE', 'DILUTION', 'LUBRICATE', 'RESTRUCTURE', 'BREAKDOWN'];
const RESISTANCE_TYPES = ['CONCEPTUAL', 'EMOTIONAL', 'PROCEDURAL', 'CONTEXTUAL', 'INERTIAL', 'STRUCTURAL'];

// Map a viscosity regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  INVISCID: '#06b6d4',
  SUPPLE: '#0ea5e9',
  STANDARD: '#6366f1',
  STICKY: '#f59e0b',
  RIGID: '#ea580c',
  FROZEN: '#dc2626',
};

export const CognitiveViscosityPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reading' | 'shear'>('overview');

  // Readings / resistances / shears
  const [readings, setReadings] = useState<any[]>([]);
  const [resistances, setResistances] = useState<any[]>([]);
  const [shears, setShears] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    fluid_type: 'WATERLIKE',
    viscosity_score: '',
    flow_rate: '',
    shear_stress: '',
    resistance_type: 'CONCEPTUAL',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Apply shear form
  const [shearForm, setShearForm] = useState({
    agent_id: '',
    shear_force: '',
    applied_strategy: 'SHEAR_THIN',
    resulting_viscosity: '',
  });

  // Plan thinning form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'SHEAR_THIN',
    target_viscosity: '',
    current_viscosity: '',
    rationale: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveViscosity.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive viscosity stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveViscosity.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadResistances = async () => {
    try {
      const result = await api.cognitiveViscosity.listResistances();
      const list = Array.isArray(result) ? result : (result?.resistances ?? []);
      setResistances(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load resistances');
    }
  };

  const loadShears = async () => {
    try {
      const result = await api.cognitiveViscosity.listShears();
      const list = Array.isArray(result) ? result : (result?.shears ?? []);
      setShears(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load shears');
    }
  };

  // Initial load
  useEffect(() => {
    loadStats();
    loadReadings();
  }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadResistances();
      loadShears();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      fluid_type: readingForm.fluid_type,
      viscosity_score: readingForm.viscosity_score.trim() === '' ? 0.5 : Number(readingForm.viscosity_score),
      flow_rate: readingForm.flow_rate.trim() === '' ? 0 : Number(readingForm.flow_rate),
      shear_stress: readingForm.shear_stress.trim() === '' ? 0 : Number(readingForm.shear_stress),
      resistance_type: readingForm.resistance_type,
    };
    try {
      await api.cognitiveViscosity.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', fluid_type: 'WATERLIKE', viscosity_score: '', flow_rate: '', shear_stress: '', resistance_type: 'CONCEPTUAL' });
      await loadReadings();
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
      const result = await api.cognitiveViscosity.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanThinning = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_viscosity: planForm.target_viscosity.trim() === '' ? 0 : Number(planForm.target_viscosity),
      current_viscosity: planForm.current_viscosity.trim() === '' ? 0 : Number(planForm.current_viscosity),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveViscosity.planThinning(payload);
      toast.success('Thinning plan created');
      setPlanForm({ agent_id: '', strategy: 'SHEAR_THIN', target_viscosity: '', current_viscosity: '', rationale: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyShear = async () => {
    if (!shearForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: shearForm.agent_id.trim(),
      shear_force: shearForm.shear_force.trim() === '' ? 0 : Number(shearForm.shear_force),
      applied_strategy: shearForm.applied_strategy,
      resulting_viscosity: shearForm.resulting_viscosity.trim() === '' ? 0 : Number(shearForm.resulting_viscosity),
    };
    try {
      await api.cognitiveViscosity.applyShear(payload);
      toast.success('Shear applied');
      setShearForm({ agent_id: '', shear_force: '', applied_strategy: 'SHEAR_THIN', resulting_viscosity: '' });
      await loadShears();
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
          <h2>🌊 Cognitive Viscosity Engine</h2>
          <p className="panel-subtitle">Record fluid readings, measure resistance, and apply shear forces across the cognitive viscosity system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive viscosity...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌊 Cognitive Viscosity Engine</h2>
        <p className="panel-subtitle">Record fluid readings, measure resistance, and apply shear forces across the cognitive viscosity system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_resistances ?? '-'}</span><span className="stat-label">Resistances</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_shears ?? '-'}</span><span className="stat-label">Shears</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_viscosity ?? '-'}</span><span className="stat-label">Avg Viscosity</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reading', 'shear'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Viscosity Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Agents</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_agents ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Readings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_readings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Resistances</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_resistances ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Shears</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_shears ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Viscosity</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_viscosity ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dominant Regime</div>
                <div style={{ fontSize: 18, color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Readings</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one in the Reading section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.fluid_type ? ` · ${r.fluid_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.fluid_type && renderBadge(r.fluid_type, themeColors.secondary)}
                          {typeof r.viscosity_score !== 'undefined' && renderBadge(`viscosity ${r.viscosity_score}`, themeColors.primary)}
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Resistances</h3>
            <button onClick={() => loadResistances()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {resistances.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No resistances measured. Measure one in the Reading section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {resistances.slice(0, 10).map((r: any, i: number) => {
                  const id = r.measurement_id ?? r.resistance_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>measurement {id}{r.source ? ` · ${r.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.resistance_type && renderBadge(r.resistance_type, themeColors.secondary)}
                          {typeof r.resistance_level !== 'undefined' && renderBadge(`level ${r.resistance_level}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Shears</h3>
            <button onClick={() => loadShears()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {shears.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No shears applied. Apply one in the Shear section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {shears.slice(0, 10).map((s: any, i: number) => {
                  const id = s.record_id ?? s.shear_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>shear record {id}{s.applied_strategy ? ` · ${s.applied_strategy}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.applied_strategy && renderBadge(s.applied_strategy, themeColors.secondary)}
                          {typeof s.shear_force !== 'undefined' && renderBadge(`force ${s.shear_force}`, themeColors.primary)}
                          {typeof s.resulting_viscosity !== 'undefined' && renderBadge(`result ${s.resulting_viscosity}`, themeColors.secondary)}
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

      {/* Reading Section */}
      {activeSection === 'reading' && (
        <div className="dashboard-section">
          {/* Record Reading */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reading</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Fluid Type</label>
                <select className="form-select" value={readingForm.fluid_type} onChange={e => setReadingForm({ ...readingForm, fluid_type: e.target.value })}>
                  {FLUID_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Resistance Type</label>
                <select className="form-select" value={readingForm.resistance_type} onChange={e => setReadingForm({ ...readingForm, resistance_type: e.target.value })}>
                  {RESISTANCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Viscosity Score</label>
                <input className="form-input" value={readingForm.viscosity_score} onChange={e => setReadingForm({ ...readingForm, viscosity_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>Flow Rate</label>
                <input className="form-input" value={readingForm.flow_rate} onChange={e => setReadingForm({ ...readingForm, flow_rate: e.target.value })} type="number" step="0.01" placeholder="e.g. 1.2" />
              </div>
              <div className="form-group">
                <label>Shear Stress</label>
                <input className="form-input" value={readingForm.shear_stress} onChange={e => setReadingForm({ ...readingForm, shear_stress: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.8" />
              </div>
            </div>
            <button onClick={handleRecordReading} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reading</button>
          </div>

          {/* Take Snapshot */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Take Snapshot</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={snapshotForm.agent_id} onChange={e => setSnapshotForm({ ...snapshotForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
            </div>
            <button onClick={handleTakeSnapshot} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Take Snapshot</button>
            {snapshotResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(snapshotResult, null, 2)}</pre>
            )}
          </div>

          {/* Plan Thinning */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Plan Thinning</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {THINNING_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Viscosity</label>
                <input className="form-input" value={planForm.target_viscosity} onChange={e => setPlanForm({ ...planForm, target_viscosity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.2" />
              </div>
              <div className="form-group">
                <label>Current Viscosity</label>
                <input className="form-input" value={planForm.current_viscosity} onChange={e => setPlanForm({ ...planForm, current_viscosity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for thinning strategy" />
              </div>
            </div>
            <button onClick={handlePlanThinning} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Thinning</button>
          </div>
        </div>
      )}

      {/* Shear Section */}
      {activeSection === 'shear' && (
        <div className="dashboard-section">
          {/* Apply Shear */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Shear</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={shearForm.agent_id} onChange={e => setShearForm({ ...shearForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Applied Strategy</label>
                <select className="form-select" value={shearForm.applied_strategy} onChange={e => setShearForm({ ...shearForm, applied_strategy: e.target.value })}>
                  {THINNING_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Shear Force</label>
                <input className="form-input" value={shearForm.shear_force} onChange={e => setShearForm({ ...shearForm, shear_force: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 1.5" />
              </div>
              <div className="form-group">
                <label>Resulting Viscosity</label>
                <input className="form-input" value={shearForm.resulting_viscosity} onChange={e => setShearForm({ ...shearForm, resulting_viscosity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.3" />
              </div>
            </div>
            <button onClick={handleApplyShear} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Shear</button>
          </div>

          {/* Shears List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Shears ({shears.length})</h3>
            <button onClick={() => loadShears()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {shears.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No shears applied. Apply one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {shears.slice(0, 30).map((s: any, i: number) => {
                  const id = s.record_id ?? s.shear_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>shear record {id}{s.applied_strategy ? ` · ${s.applied_strategy}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.applied_strategy && renderBadge(s.applied_strategy, themeColors.secondary)}
                          {typeof s.shear_force !== 'undefined' && renderBadge(`force ${s.shear_force}`, themeColors.primary)}
                          {typeof s.resulting_viscosity !== 'undefined' && renderBadge(`result ${s.resulting_viscosity}`, themeColors.secondary)}
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

export default CognitiveViscosityPanel;
