import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: slate for cognitive drift
const themeColors = {
  primary: '#475569',
  secondary: '#64748b',
  bg: '#f8fafc',
  border: '#cbd5e1',
  accent: '#e2e8f0',
  text: '#1e293b',
};

// Enum values must match backend DriftAxis / BoundaryState / DriftSignature / AnchoringStrategy / DriftCause exactly (uppercase).
const DRIFT_AXES = ['SEMANTIC', 'PRAGMATIC', 'EMOTIONAL', 'EPISTEMIC', 'NORMATIVE', 'AESTHETIC'];
const BOUNDARY_STATES = ['RIGID', 'FIRM', 'POROUS', 'BREATHING', 'FLUID', 'DISSOLVED'];
const DRIFT_SIGNATURES = ['NEUTRAL', 'MONOTONIC', 'CYCLICAL', 'EXPONENTIAL', 'STEP', 'RANDOM_WALK'];
const ANCHORING_STRATEGIES = ['HOLD', 'TIGHTEN', 'LOOSEN', 'RELEASE', 'RE_CENTER', 'WIDEN'];
const DRIFT_CAUSES = ['EXTERNAL_PRESSURE', 'INTERNAL_REASONING', 'EVIDENCE', 'INTUITION', 'SOCIAL_CUE', 'NOVELTY'];

// Map a boundary state value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  RIGID: '#0f172a',
  FIRM: '#334155',
  POROUS: '#64748b',
  BREATHING: '#0ea5e9',
  FLUID: '#06b6d4',
  DISSOLVED: '#a855f7',
};

export const CognitiveDriftPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'readings' | 'shifts' | 'snapshots' | 'plans' | 'calibrations'>('overview');

  // Readings / shifts / snapshots / plans / calibrations
  const [readings, setReadings] = useState<any[]>([]);
  const [shifts, setShifts] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [calibrations, setCalibrations] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'SEMANTIC',
    drift_magnitude: '',
    direction: '',
    boundary_state: 'FIRM',
    signature: 'NEUTRAL',
    notes: '',
  });

  // Record shift form
  const [shiftForm, setShiftForm] = useState({
    agent_id: '',
    axis: 'SEMANTIC',
    from_boundary: 'FIRM',
    to_boundary: 'FIRM',
    magnitude: '',
    cause: 'INTERNAL_REASONING',
    notes: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan anchoring form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'HOLD',
    target_drift: '',
    rationale: '',
  });

  // Record calibration form
  const [calibrationForm, setCalibrationForm] = useState({
    agent_id: '',
    axis: 'SEMANTIC',
    expected_drift: '',
    observed_drift: '',
    correction: '',
    notes: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveDrift.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive drift stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveDrift.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadShifts = async () => {
    try {
      const result = await api.cognitiveDrift.listShifts();
      const list = Array.isArray(result) ? result : (result?.shifts ?? []);
      setShifts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load shifts');
    }
  };

  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveDrift.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveDrift.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  const loadCalibrations = async () => {
    try {
      const result = await api.cognitiveDrift.listCalibrations();
      const list = Array.isArray(result) ? result : (result?.calibrations ?? []);
      setCalibrations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load calibrations');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadShifts();
      loadSnapshots();
      loadPlans();
      loadCalibrations();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      drift_magnitude: readingForm.drift_magnitude.trim() === '' ? 0 : Number(readingForm.drift_magnitude),
      direction: readingForm.direction.trim() === '' ? 0 : Number(readingForm.direction),
      boundary_state: readingForm.boundary_state,
      signature: readingForm.signature,
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveDrift.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', axis: 'SEMANTIC', drift_magnitude: '', direction: '', boundary_state: 'FIRM', signature: 'NEUTRAL', notes: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordShift = async () => {
    if (!shiftForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: shiftForm.agent_id.trim(),
      axis: shiftForm.axis,
      from_boundary: shiftForm.from_boundary,
      to_boundary: shiftForm.to_boundary,
      magnitude: shiftForm.magnitude.trim() === '' ? 0 : Number(shiftForm.magnitude),
      cause: shiftForm.cause,
    };
    if (shiftForm.notes) payload.notes = shiftForm.notes.trim();
    try {
      await api.cognitiveDrift.recordShift(payload);
      toast.success('Shift recorded');
      setShiftForm({ agent_id: '', axis: 'SEMANTIC', from_boundary: 'FIRM', to_boundary: 'FIRM', magnitude: '', cause: 'INTERNAL_REASONING', notes: '' });
      await loadShifts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      const result = await api.cognitiveDrift.takeSnapshot({ agent_id: snapshotForm.agent_id.trim() });
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanAnchoring = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_drift: planForm.target_drift.trim() === '' ? 0 : Number(planForm.target_drift),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveDrift.planAnchoring(payload);
      toast.success('Anchoring plan created');
      setPlanForm({ agent_id: '', strategy: 'HOLD', target_drift: '', rationale: '' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordCalibration = async () => {
    if (!calibrationForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: calibrationForm.agent_id.trim(),
      axis: calibrationForm.axis,
      expected_drift: calibrationForm.expected_drift.trim() === '' ? 0 : Number(calibrationForm.expected_drift),
      observed_drift: calibrationForm.observed_drift.trim() === '' ? 0 : Number(calibrationForm.observed_drift),
      correction: calibrationForm.correction.trim() === '' ? 0 : Number(calibrationForm.correction),
    };
    if (calibrationForm.notes) payload.notes = calibrationForm.notes.trim();
    try {
      await api.cognitiveDrift.recordCalibration(payload);
      toast.success('Calibration recorded');
      setCalibrationForm({ agent_id: '', axis: 'SEMANTIC', expected_drift: '', observed_drift: '', correction: '', notes: '' });
      await loadCalibrations();
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
          <h2>🌊 Cognitive Drift</h2>
          <p className="panel-subtitle">Track semantic, pragmatic, and epistemic drift across the cognitive boundary system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive drift...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌊 Cognitive Drift</h2>
        <p className="panel-subtitle">Track semantic, pragmatic, and epistemic drift across the cognitive boundary system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_shifts ?? '-'}</span><span className="stat-label">Shifts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_drift ?? '-'}</span><span className="stat-label">Avg Drift</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'shifts', 'snapshots', 'plans', 'calibrations'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Drift Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Shifts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_shifts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Drift</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_drift ?? 0}</div>
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
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one in the Readings section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.axis ? ` · ${r.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.boundary_state && renderBadge(r.boundary_state, statusColor(r.boundary_state))}
                          {typeof r.drift_magnitude !== 'undefined' && renderBadge(`drift ${r.drift_magnitude}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Shifts</h3>
            <button onClick={() => loadShifts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {shifts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No shifts recorded. Record one in the Shifts section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {shifts.slice(0, 10).map((s: any, i: number) => {
                  const id = s.shift_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>shift {id}{s.cause ? ` · ${s.cause}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.axis && renderBadge(s.axis, themeColors.secondary)}
                          {s.from_boundary && s.to_boundary && renderBadge(`${s.from_boundary}->${s.to_boundary}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Calibrations</h3>
            <button onClick={() => loadCalibrations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {calibrations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No calibrations recorded. Record one in the Calibrations section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {calibrations.slice(0, 10).map((c: any, i: number) => {
                  const id = c.calibration_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>calibration {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.axis && renderBadge(c.axis, themeColors.secondary)}
                          {typeof c.correction !== 'undefined' && renderBadge(`corr ${c.correction}`, themeColors.primary)}
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

      {/* Readings Section */}
      {activeSection === 'readings' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reading</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={readingForm.axis} onChange={e => setReadingForm({ ...readingForm, axis: e.target.value })}>
                  {DRIFT_AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Boundary State</label>
                <select className="form-select" value={readingForm.boundary_state} onChange={e => setReadingForm({ ...readingForm, boundary_state: e.target.value })}>
                  {BOUNDARY_STATES.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Signature</label>
                <select className="form-select" value={readingForm.signature} onChange={e => setReadingForm({ ...readingForm, signature: e.target.value })}>
                  {DRIFT_SIGNATURES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Drift Magnitude</label>
                <input className="form-input" value={readingForm.drift_magnitude} onChange={e => setReadingForm({ ...readingForm, drift_magnitude: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.3" />
              </div>
              <div className="form-group">
                <label>Direction</label>
                <input className="form-input" value={readingForm.direction} onChange={e => setReadingForm({ ...readingForm, direction: e.target.value })} type="number" min="-1" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={readingForm.notes} onChange={e => setReadingForm({ ...readingForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordReading} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reading</button>
          </div>

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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.axis ? ` · ${r.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.boundary_state && renderBadge(r.boundary_state, statusColor(r.boundary_state))}
                          {typeof r.drift_magnitude !== 'undefined' && renderBadge(`drift ${r.drift_magnitude}`, themeColors.primary)}
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

      {/* Shifts Section */}
      {activeSection === 'shifts' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Shift</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={shiftForm.agent_id} onChange={e => setShiftForm({ ...shiftForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={shiftForm.axis} onChange={e => setShiftForm({ ...shiftForm, axis: e.target.value })}>
                  {DRIFT_AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>From Boundary</label>
                <select className="form-select" value={shiftForm.from_boundary} onChange={e => setShiftForm({ ...shiftForm, from_boundary: e.target.value })}>
                  {BOUNDARY_STATES.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Boundary</label>
                <select className="form-select" value={shiftForm.to_boundary} onChange={e => setShiftForm({ ...shiftForm, to_boundary: e.target.value })}>
                  {BOUNDARY_STATES.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Magnitude</label>
                <input className="form-input" value={shiftForm.magnitude} onChange={e => setShiftForm({ ...shiftForm, magnitude: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>Cause</label>
                <select className="form-select" value={shiftForm.cause} onChange={e => setShiftForm({ ...shiftForm, cause: e.target.value })}>
                  {DRIFT_CAUSES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={shiftForm.notes} onChange={e => setShiftForm({ ...shiftForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordShift} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Shift</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Shifts ({shifts.length})</h3>
            <button onClick={() => loadShifts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {shifts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No shifts recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {shifts.slice(0, 30).map((s: any, i: number) => {
                  const id = s.shift_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>shift {id}{s.cause ? ` · ${s.cause}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.axis && renderBadge(s.axis, themeColors.secondary)}
                          {s.from_boundary && s.to_boundary && renderBadge(`${s.from_boundary}->${s.to_boundary}`, themeColors.primary)}
                          {typeof s.magnitude !== 'undefined' && renderBadge(`mag ${s.magnitude}`, themeColors.secondary)}
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

      {/* Snapshots Section */}
      {activeSection === 'snapshots' && (
        <div className="dashboard-section">
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

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Snapshots ({snapshots.length})</h3>
            <button onClick={() => loadSnapshots()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {snapshots.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No snapshots taken. Take one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {snapshots.slice(0, 30).map((s: any, i: number) => {
                  const id = s.snapshot_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>snapshot {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
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

      {/* Plans Section */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Anchoring</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {ANCHORING_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Drift</label>
                <input className="form-input" value={planForm.target_drift} onChange={e => setPlanForm({ ...planForm, target_drift: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.2" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for plan" />
              </div>
            </div>
            <button onClick={handlePlanAnchoring} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Anchoring</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Plans ({plans.length})</h3>
            <button onClick={() => loadPlans()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {plans.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No plans created. Create one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {plans.slice(0, 30).map((p: any, i: number) => {
                  const id = p.plan_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>plan {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.strategy && renderBadge(p.strategy, themeColors.secondary)}
                          {typeof p.target_drift !== 'undefined' && renderBadge(`drift ${p.target_drift}`, themeColors.primary)}
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

      {/* Calibrations Section */}
      {activeSection === 'calibrations' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Calibration</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={calibrationForm.agent_id} onChange={e => setCalibrationForm({ ...calibrationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={calibrationForm.axis} onChange={e => setCalibrationForm({ ...calibrationForm, axis: e.target.value })}>
                  {DRIFT_AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Drift</label>
                <input className="form-input" value={calibrationForm.expected_drift} onChange={e => setCalibrationForm({ ...calibrationForm, expected_drift: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.2" />
              </div>
              <div className="form-group">
                <label>Observed Drift</label>
                <input className="form-input" value={calibrationForm.observed_drift} onChange={e => setCalibrationForm({ ...calibrationForm, observed_drift: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.35" />
              </div>
              <div className="form-group">
                <label>Correction</label>
                <input className="form-input" value={calibrationForm.correction} onChange={e => setCalibrationForm({ ...calibrationForm, correction: e.target.value })} type="number" step="0.01" placeholder="e.g. -0.15" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={calibrationForm.notes} onChange={e => setCalibrationForm({ ...calibrationForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordCalibration} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Calibration</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Calibrations ({calibrations.length})</h3>
            <button onClick={() => loadCalibrations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {calibrations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No calibrations recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {calibrations.slice(0, 30).map((c: any, i: number) => {
                  const id = c.calibration_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>calibration {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.axis && renderBadge(c.axis, themeColors.secondary)}
                          {typeof c.expected_drift !== 'undefined' && renderBadge(`exp ${c.expected_drift}`, themeColors.primary)}
                          {typeof c.observed_drift !== 'undefined' && renderBadge(`obs ${c.observed_drift}`, themeColors.secondary)}
                          {typeof c.correction !== 'undefined' && renderBadge(`corr ${c.correction}`, themeColors.primary)}
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

export default CognitiveDriftPanel;
