import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: pink for cognitive cadence
const themeColors = {
  primary: '#db2777',
  secondary: '#ec4899',
  bg: '#fdf2f8',
  border: '#fbcfe8',
  accent: '#fce7f3',
  text: '#831843',
};

// Enum values must match backend BeatType / PulseState / CadenceRegime / RhythmStrategy / DriftIndicator exactly (uppercase).
const BEAT_TYPES = ['SYLLABLE', 'PHRASE', 'CLAUSE', 'ARGUMENT', 'NARRATIVE', 'EPOCH'];
const PULSE_STATES = ['SILENT', 'TICKING', 'STEADY', 'SURGING', 'STUTTERING', 'SYNCOPATED'];
const CADENCE_REGIMES = ['STACCATO', 'MEASURED', 'FLOWING', 'STACCATO_HARD', 'RIGID', 'ERRATIC'];
const RHYTHM_STRATEGIES = ['SLOW_DOWN', 'SPEED_UP', 'STEADY', 'RESET', 'SILENCE', 'OVERDRIVE'];
const DRIFT_INDICATORS = ['NONE', 'DRIFTING_FAST', 'DRIFTING_SLOW', 'STABILIZING', 'LOCKED', 'CHAOTIC'];

// Map a pulse state value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  SILENT: '#6b7280',
  TICKING: '#0ea5e9',
  STEADY: '#16a34a',
  SURGING: '#f59e0b',
  STUTTERING: '#ea580c',
  SYNCOPATED: '#a855f7',
};

export const CognitiveCadencePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'readings' | 'beats' | 'snapshots' | 'plans' | 'pulses'>('overview');

  // Readings / beats / snapshots / plans / pulses
  const [readings, setReadings] = useState<any[]>([]);
  const [beats, setBeats] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [pulses, setPulses] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    beat_type: 'SYLLABLE',
    tempo_score: '',
    interval_ms: '',
    pulse_state: 'STEADY',
    intensity: '',
    notes: '',
  });

  // Record beat form
  const [beatForm, setBeatForm] = useState({
    agent_id: '',
    beat_type: 'SYLLABLE',
    period_ms: '',
    amplitude: '',
    source: '',
    notes: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan rhythm form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'STEADY',
    target_tempo: '',
    rationale: '',
  });

  // Record pulse form
  const [pulseForm, setPulseForm] = useState({
    agent_id: '',
    from_state: 'STEADY',
    to_state: 'STEADY',
    interval_ms: '',
    drift_indicator: 'NONE',
    notes: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveCadence.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive cadence stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveCadence.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadBeats = async () => {
    try {
      const result = await api.cognitiveCadence.listBeats();
      const list = Array.isArray(result) ? result : (result?.beats ?? []);
      setBeats(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load beats');
    }
  };

  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveCadence.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveCadence.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  const loadPulses = async () => {
    try {
      const result = await api.cognitiveCadence.listPulses();
      const list = Array.isArray(result) ? result : (result?.pulses ?? []);
      setPulses(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load pulses');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadBeats();
      loadSnapshots();
      loadPlans();
      loadPulses();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      beat_type: readingForm.beat_type,
      tempo_score: readingForm.tempo_score.trim() === '' ? 0.5 : Number(readingForm.tempo_score),
      interval_ms: readingForm.interval_ms.trim() === '' ? 0 : Number(readingForm.interval_ms),
      pulse_state: readingForm.pulse_state,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveCadence.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', beat_type: 'SYLLABLE', tempo_score: '', interval_ms: '', pulse_state: 'STEADY', intensity: '', notes: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordBeat = async () => {
    if (!beatForm.agent_id.trim() || !beatForm.source.trim()) {
      toast.error('Agent ID and source are required');
      return;
    }
    const payload: any = {
      agent_id: beatForm.agent_id.trim(),
      beat_type: beatForm.beat_type,
      period_ms: beatForm.period_ms.trim() === '' ? 0 : Number(beatForm.period_ms),
      amplitude: beatForm.amplitude.trim() === '' ? 0 : Number(beatForm.amplitude),
      source: beatForm.source.trim(),
    };
    if (beatForm.notes) payload.notes = beatForm.notes.trim();
    try {
      await api.cognitiveCadence.recordBeat(payload);
      toast.success('Beat recorded');
      setBeatForm({ agent_id: '', beat_type: 'SYLLABLE', period_ms: '', amplitude: '', source: '', notes: '' });
      await loadBeats();
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
      const result = await api.cognitiveCadence.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanRhythm = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_tempo: planForm.target_tempo.trim() === '' ? 0 : Number(planForm.target_tempo),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveCadence.planRhythm(payload);
      toast.success('Rhythm plan created');
      setPlanForm({ agent_id: '', strategy: 'STEADY', target_tempo: '', rationale: '' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordPulse = async () => {
    if (!pulseForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: pulseForm.agent_id.trim(),
      from_state: pulseForm.from_state,
      to_state: pulseForm.to_state,
      interval_ms: pulseForm.interval_ms.trim() === '' ? 0 : Number(pulseForm.interval_ms),
      drift_indicator: pulseForm.drift_indicator,
    };
    if (pulseForm.notes) payload.notes = pulseForm.notes.trim();
    try {
      await api.cognitiveCadence.recordPulse(payload);
      toast.success('Pulse recorded');
      setPulseForm({ agent_id: '', from_state: 'STEADY', to_state: 'STEADY', interval_ms: '', drift_indicator: 'NONE', notes: '' });
      await loadPulses();
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
          <h2>🎵 Cognitive Cadence</h2>
          <p className="panel-subtitle">Record rhythmic readings, capture beats, and plan tempo adjustments across the cognitive cadence system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive cadence...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🎵 Cognitive Cadence</h2>
        <p className="panel-subtitle">Record rhythmic readings, capture beats, and plan tempo adjustments across the cognitive cadence system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_beats ?? '-'}</span><span className="stat-label">Beats</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_pulses ?? '-'}</span><span className="stat-label">Pulses</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'beats', 'snapshots', 'plans', 'pulses'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Cadence Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Beats</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_beats ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Pulses</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_pulses ?? 0}</div>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.beat_type ? ` · ${r.beat_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.beat_type && renderBadge(r.beat_type, themeColors.secondary)}
                          {r.pulse_state && renderBadge(r.pulse_state, statusColor(r.pulse_state))}
                          {typeof r.tempo_score !== 'undefined' && renderBadge(`tempo ${r.tempo_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Beats</h3>
            <button onClick={() => loadBeats()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {beats.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No beats captured. Capture one in the Beats section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {beats.slice(0, 10).map((b: any, i: number) => {
                  const id = b.beat_id ?? b.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {b.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>beat {id}{b.source ? ` · ${b.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {b.beat_type && renderBadge(b.beat_type, themeColors.secondary)}
                          {typeof b.period_ms !== 'undefined' && renderBadge(`period ${b.period_ms}ms`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Pulses</h3>
            <button onClick={() => loadPulses()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {pulses.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No pulses recorded. Record one in the Pulses section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {pulses.slice(0, 10).map((p: any, i: number) => {
                  const id = p.pulse_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>pulse {id}{p.drift_indicator ? ` · ${p.drift_indicator}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.from_state && p.to_state && renderBadge(`${p.from_state}->${p.to_state}`, themeColors.secondary)}
                          {p.drift_indicator && renderBadge(p.drift_indicator, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Snapshots &amp; Plans</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
              <button onClick={() => loadSnapshots()} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Refresh Snapshots ({snapshots.length})</button>
              <button onClick={() => loadPlans()} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Refresh Plans ({plans.length})</button>
            </div>
          </div>
        </div>
      )}

      {/* Readings Section */}
      {activeSection === 'readings' && (
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
                <label>Beat Type</label>
                <select className="form-select" value={readingForm.beat_type} onChange={e => setReadingForm({ ...readingForm, beat_type: e.target.value })}>
                  {BEAT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Pulse State</label>
                <select className="form-select" value={readingForm.pulse_state} onChange={e => setReadingForm({ ...readingForm, pulse_state: e.target.value })}>
                  {PULSE_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Tempo Score</label>
                <input className="form-input" value={readingForm.tempo_score} onChange={e => setReadingForm({ ...readingForm, tempo_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Interval (ms)</label>
                <input className="form-input" value={readingForm.interval_ms} onChange={e => setReadingForm({ ...readingForm, interval_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 500" />
              </div>
              <div className="form-group">
                <label>Intensity</label>
                <input className="form-input" value={readingForm.intensity} onChange={e => setReadingForm({ ...readingForm, intensity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={readingForm.notes} onChange={e => setReadingForm({ ...readingForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordReading} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reading</button>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.beat_type ? ` · ${r.beat_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.beat_type && renderBadge(r.beat_type, themeColors.secondary)}
                          {r.pulse_state && renderBadge(r.pulse_state, statusColor(r.pulse_state))}
                          {typeof r.tempo_score !== 'undefined' && renderBadge(`tempo ${r.tempo_score}`, themeColors.primary)}
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

      {/* Beats Section */}
      {activeSection === 'beats' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Beat</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={beatForm.agent_id} onChange={e => setBeatForm({ ...beatForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Beat Type</label>
                <select className="form-select" value={beatForm.beat_type} onChange={e => setBeatForm({ ...beatForm, beat_type: e.target.value })}>
                  {BEAT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Period (ms)</label>
                <input className="form-input" value={beatForm.period_ms} onChange={e => setBeatForm({ ...beatForm, period_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 600" />
              </div>
              <div className="form-group">
                <label>Amplitude</label>
                <input className="form-input" value={beatForm.amplitude} onChange={e => setBeatForm({ ...beatForm, amplitude: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Source *</label>
                <input className="form-input" value={beatForm.source} onChange={e => setBeatForm({ ...beatForm, source: e.target.value })} placeholder="beat source" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={beatForm.notes} onChange={e => setBeatForm({ ...beatForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordBeat} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Beat</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Beats ({beats.length})</h3>
            <button onClick={() => loadBeats()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {beats.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No beats captured. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {beats.slice(0, 30).map((b: any, i: number) => {
                  const id = b.beat_id ?? b.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {b.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>beat {id}{b.source ? ` · ${b.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {b.beat_type && renderBadge(b.beat_type, themeColors.secondary)}
                          {typeof b.period_ms !== 'undefined' && renderBadge(`period ${b.period_ms}ms`, themeColors.primary)}
                          {typeof b.amplitude !== 'undefined' && renderBadge(`amp ${b.amplitude}`, themeColors.secondary)}
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
            <h3 style={{ color: themeColors.text }}>Plan Rhythm</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {RHYTHM_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Tempo</label>
                <input className="form-input" value={planForm.target_tempo} onChange={e => setPlanForm({ ...planForm, target_tempo: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for plan" />
              </div>
            </div>
            <button onClick={handlePlanRhythm} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Rhythm</button>
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
                          {typeof p.target_tempo !== 'undefined' && renderBadge(`tempo ${p.target_tempo}`, themeColors.primary)}
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

      {/* Pulses Section */}
      {activeSection === 'pulses' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Pulse</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={pulseForm.agent_id} onChange={e => setPulseForm({ ...pulseForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>From State</label>
                <select className="form-select" value={pulseForm.from_state} onChange={e => setPulseForm({ ...pulseForm, from_state: e.target.value })}>
                  {PULSE_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To State</label>
                <select className="form-select" value={pulseForm.to_state} onChange={e => setPulseForm({ ...pulseForm, to_state: e.target.value })}>
                  {PULSE_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Interval (ms)</label>
                <input className="form-input" value={pulseForm.interval_ms} onChange={e => setPulseForm({ ...pulseForm, interval_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 500" />
              </div>
              <div className="form-group">
                <label>Drift Indicator</label>
                <select className="form-select" value={pulseForm.drift_indicator} onChange={e => setPulseForm({ ...pulseForm, drift_indicator: e.target.value })}>
                  {DRIFT_INDICATORS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={pulseForm.notes} onChange={e => setPulseForm({ ...pulseForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordPulse} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Pulse</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Pulses ({pulses.length})</h3>
            <button onClick={() => loadPulses()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {pulses.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No pulses recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {pulses.slice(0, 30).map((p: any, i: number) => {
                  const id = p.pulse_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>pulse {id}{p.drift_indicator ? ` · ${p.drift_indicator}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.from_state && p.to_state && renderBadge(`${p.from_state}->${p.to_state}`, themeColors.secondary)}
                          {p.drift_indicator && renderBadge(p.drift_indicator, themeColors.primary)}
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

export default CognitiveCadencePanel;
