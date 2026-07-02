import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: cyan for cognitive turbulence
const themeColors = {
  primary: '#0891b2',
  secondary: '#06b6d4',
  bg: '#ecfeff',
  border: '#a5f3fc',
  accent: '#cffafe',
  text: '#164e63',
};

// Enum values must match backend FlowRegime / EddyType / PerturbationSource / StabilizationStrategy / ChaosIndicator exactly (uppercase).
const FLOW_REGIMES = ['LAMINAR', 'TRANSITIONAL', 'TURBULENT', 'VORTICAL', 'SEPARATED', 'CHAOTIC'];
const EDDY_TYPES = ['MICRO', 'MESO', 'MACRO', 'COHERENT', 'DECAYING', 'FORMING'];
const PERTURBATION_SOURCES = ['EXTERNAL', 'INTERNAL', 'STRUCTURAL', 'EMOTIONAL', 'CONTEXTUAL', 'COGNITIVE'];
const STABILIZATION_STRATEGIES = ['DAMP', 'STREAMLINE', 'BYPASS', 'RESHAPING', 'ANCHOR', 'EMBRACE'];
const CHAOS_INDICATORS = ['ATTRACTOR', 'BIFURCATION', 'SENSITIVE_DEPENDENCE', 'PERIODICITY', 'FRACTAL', 'DISSIPATION'];

// Map a flow regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  LAMINAR: '#16a34a',
  TRANSITIONAL: '#65a30d',
  TURBULENT: '#f59e0b',
  VORTICAL: '#ea580c',
  SEPARATED: '#dc2626',
  CHAOTIC: '#991b1b',
};

export const CognitiveTurbulencePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reading' | 'eddy'>('overview');

  // Readings / eddies / perturbations
  const [readings, setReadings] = useState<any[]>([]);
  const [eddies, setEddies] = useState<any[]>([]);
  const [perturbations, setPerturbations] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    reynolds_number: '',
    turbulence_intensity: '',
    regime: 'LAMINAR',
    dominant_eddy: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Detect eddy form
  const [eddyForm, setEddyForm] = useState({
    agent_id: '',
    eddy_type: 'MICRO',
    strength: '',
    persistence: '',
    source: '',
  });

  // Apply perturbation form
  const [perturbationForm, setPerturbationForm] = useState({
    agent_id: '',
    source: 'EXTERNAL',
    perturbation_strength: '',
    resulting_turbulence: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveTurbulence.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive turbulence stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveTurbulence.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadEddies = async () => {
    try {
      const result = await api.cognitiveTurbulence.listEddies();
      const list = Array.isArray(result) ? result : (result?.eddies ?? []);
      setEddies(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load eddies');
    }
  };

  const loadPerturbations = async () => {
    try {
      const result = await api.cognitiveTurbulence.listPerturbations();
      const list = Array.isArray(result) ? result : (result?.perturbations ?? []);
      setPerturbations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load perturbations');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); loadReadings(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadEddies();
      loadPerturbations();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      reynolds_number: readingForm.reynolds_number.trim() === '' ? 0 : Number(readingForm.reynolds_number),
      turbulence_intensity: readingForm.turbulence_intensity.trim() === '' ? 0 : Number(readingForm.turbulence_intensity),
      regime: readingForm.regime,
    };
    if (readingForm.dominant_eddy.trim()) payload.dominant_eddy = readingForm.dominant_eddy.trim();
    try {
      await api.cognitiveTurbulence.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', reynolds_number: '', turbulence_intensity: '', regime: 'LAMINAR', dominant_eddy: '' });
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
      const result = await api.cognitiveTurbulence.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDetectEddy = async () => {
    if (!eddyForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: eddyForm.agent_id.trim(),
      eddy_type: eddyForm.eddy_type,
      strength: eddyForm.strength.trim() === '' ? 0.5 : Number(eddyForm.strength),
      persistence: eddyForm.persistence.trim() === '' ? 0.5 : Number(eddyForm.persistence),
      source: eddyForm.source.trim(),
    };
    try {
      await api.cognitiveTurbulence.detectEddy(payload);
      toast.success('Eddy detected');
      setEddyForm({ agent_id: '', eddy_type: 'MICRO', strength: '', persistence: '', source: '' });
      await loadEddies();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyPerturbation = async () => {
    if (!perturbationForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: perturbationForm.agent_id.trim(),
      source: perturbationForm.source,
      perturbation_strength: perturbationForm.perturbation_strength.trim() === '' ? 0.5 : Number(perturbationForm.perturbation_strength),
      resulting_turbulence: perturbationForm.resulting_turbulence.trim() === '' ? 0.5 : Number(perturbationForm.resulting_turbulence),
    };
    try {
      await api.cognitiveTurbulence.applyPerturbation(payload);
      toast.success('Perturbation applied');
      setPerturbationForm({ agent_id: '', source: 'EXTERNAL', perturbation_strength: '', resulting_turbulence: '' });
      await loadPerturbations();
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
          <h2>🌪️ Cognitive Turbulence Engine</h2>
          <p className="panel-subtitle">Record turbulence readings, detect eddies, and apply perturbations across the cognitive flow system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive turbulence...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌪️ Cognitive Turbulence Engine</h2>
        <p className="panel-subtitle">Record turbulence readings, detect eddies, and apply perturbations across the cognitive flow system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Total Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_eddies ?? '-'}</span><span className="stat-label">Eddies</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_perturbations ?? '-'}</span><span className="stat-label">Perturbations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_turbulence ?? '-'}</span><span className="stat-label">Avg Turbulence</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reading', 'eddy'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Turbulence Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Eddies</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_eddies ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Perturbations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_perturbations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Turbulence</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_turbulence ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dominant Regime</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</div>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.dominant_eddy ? ` · ${r.dominant_eddy}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
                          {typeof r.turbulence_intensity !== 'undefined' && renderBadge(`intensity ${r.turbulence_intensity}`, themeColors.secondary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Eddies</h3>
            <button onClick={() => loadEddies()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {eddies.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No eddies detected. Detect one in the Eddy section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {eddies.slice(0, 10).map((e: any, i: number) => {
                  const id = e.eddy_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>eddy {id}{e.source ? ` · ${e.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.eddy_type && renderBadge(e.eddy_type, themeColors.secondary)}
                          {typeof e.strength !== 'undefined' && renderBadge(`strength ${e.strength}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Perturbations</h3>
            <button onClick={() => loadPerturbations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {perturbations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No perturbations applied. Apply one in the Eddy section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {perturbations.slice(0, 10).map((p: any, i: number) => {
                  const id = p.perturbation_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>perturbation {id}{p.source ? ` · ${p.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.source && renderBadge(p.source, themeColors.secondary)}
                          {typeof p.perturbation_strength !== 'undefined' && renderBadge(`strength ${p.perturbation_strength}`, themeColors.primary)}
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
                <label>Reynolds Number</label>
                <input className="form-input" value={readingForm.reynolds_number} onChange={e => setReadingForm({ ...readingForm, reynolds_number: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 2300" />
              </div>
              <div className="form-group">
                <label>Turbulence Intensity</label>
                <input className="form-input" value={readingForm.turbulence_intensity} onChange={e => setReadingForm({ ...readingForm, turbulence_intensity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>Regime</label>
                <select className="form-select" value={readingForm.regime} onChange={e => setReadingForm({ ...readingForm, regime: e.target.value })}>
                  {FLOW_REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Dominant Eddy</label>
                <input className="form-input" value={readingForm.dominant_eddy} onChange={e => setReadingForm({ ...readingForm, dominant_eddy: e.target.value })} placeholder="dominant eddy identifier" />
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

          {/* Readings List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Readings ({readings.length})</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 30).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.dominant_eddy ? ` · ${r.dominant_eddy}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
                          {typeof r.turbulence_intensity !== 'undefined' && renderBadge(`intensity ${r.turbulence_intensity}`, themeColors.secondary)}
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

      {/* Eddy Section */}
      {activeSection === 'eddy' && (
        <div className="dashboard-section">
          {/* Detect Eddy */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Detect Eddy</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={eddyForm.agent_id} onChange={e => setEddyForm({ ...eddyForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Eddy Type</label>
                <select className="form-select" value={eddyForm.eddy_type} onChange={e => setEddyForm({ ...eddyForm, eddy_type: e.target.value })}>
                  {EDDY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strength</label>
                <input className="form-input" value={eddyForm.strength} onChange={e => setEddyForm({ ...eddyForm, strength: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group">
                <label>Persistence</label>
                <input className="form-input" value={eddyForm.persistence} onChange={e => setEddyForm({ ...eddyForm, persistence: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Source</label>
                <input className="form-input" value={eddyForm.source} onChange={e => setEddyForm({ ...eddyForm, source: e.target.value })} placeholder="eddy source" />
              </div>
            </div>
            <button onClick={handleDetectEddy} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Detect Eddy</button>
          </div>

          {/* Apply Perturbation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Perturbation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={perturbationForm.agent_id} onChange={e => setPerturbationForm({ ...perturbationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Source</label>
                <select className="form-select" value={perturbationForm.source} onChange={e => setPerturbationForm({ ...perturbationForm, source: e.target.value })}>
                  {PERTURBATION_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Perturbation Strength</label>
                <input className="form-input" value={perturbationForm.perturbation_strength} onChange={e => setPerturbationForm({ ...perturbationForm, perturbation_strength: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Resulting Turbulence</label>
                <input className="form-input" value={perturbationForm.resulting_turbulence} onChange={e => setPerturbationForm({ ...perturbationForm, resulting_turbulence: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.55" />
              </div>
            </div>
            <button onClick={handleApplyPerturbation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Perturbation</button>
          </div>

          {/* Eddies List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Eddies ({eddies.length})</h3>
            <button onClick={() => loadEddies()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {eddies.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No eddies detected. Detect one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {eddies.slice(0, 30).map((e: any, i: number) => {
                  const id = e.eddy_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>eddy {id}{e.source ? ` · ${e.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.eddy_type && renderBadge(e.eddy_type, themeColors.secondary)}
                          {typeof e.strength !== 'undefined' && renderBadge(`strength ${e.strength}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Perturbations List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Perturbations ({perturbations.length})</h3>
            <button onClick={() => loadPerturbations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {perturbations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No perturbations applied. Apply one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {perturbations.slice(0, 30).map((p: any, i: number) => {
                  const id = p.perturbation_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>perturbation {id}{p.source ? ` · ${p.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.source && renderBadge(p.source, themeColors.secondary)}
                          {typeof p.perturbation_strength !== 'undefined' && renderBadge(`strength ${p.perturbation_strength}`, themeColors.primary)}
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

export default CognitiveTurbulencePanel;
