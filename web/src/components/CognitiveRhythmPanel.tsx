import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: cyan for cognitive rhythm
const themeColors = {
  primary: '#0891b2',
  secondary: '#06b6d4',
  bg: '#ecfeff',
  border: '#a5f3fc',
  accent: '#cffafe',
  text: '#164e63',
};

// Enum values must match backend RhythmPhase / RhythmRegime / CycleType / AlignmentStrategy / RhythmTrend exactly (uppercase).
const RHYTHM_PHASES = ['FOCUS', 'CREATIVE_BURST', 'CONSOLIDATION', 'REST', 'TRANSITION'];
const RHYTHM_REGIMES = ['ARRHYTHMIC', 'IRREGULAR', 'REGULAR', 'HARMONIC', 'SYNCOPATED'];
const CYCLE_TYPES = ['ULTRADIAN', 'CIRCADIAN', 'INFRADIAN', 'SESSION', 'TASK'];
const ALIGNMENT_STRATEGIES = ['MATCH_PHASE', 'DEFER_TASK', 'FORCE_PHASE', 'ALTERNATE', 'BATCH'];
const RHYTHM_TRENDS = ['ACCELERATING', 'DECELERATING', 'STABLE', 'DRIFTING', 'DISRUPTING'];

// Map a rhythm regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  ARRHYTHMIC: '#dc2626',
  IRREGULAR: '#f97316',
  REGULAR: '#0ea5e9',
  HARMONIC: '#16a34a',
  SYNCOPATED: '#8b5cf6',
};

export const CognitiveRhythmPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'pulse' | 'alignment'>('overview');

  // Pulses / cycles / alignments
  const [pulses, setPulses] = useState<any[]>([]);
  const [cycles, setCycles] = useState<any[]>([]);
  const [alignments, setAlignments] = useState<any[]>([]);
  const [trendResult, setTrendResult] = useState<any>(null);

  // Record pulse form
  const [pulseForm, setPulseForm] = useState({
    agent_id: '',
    phase: 'FOCUS',
    intensity: '',
    regime: 'REGULAR',
  });

  // Measure cycle form
  const [cycleForm, setCycleForm] = useState({
    agent_id: '',
    cycle_type: 'ULTRADIAN',
    period: '',
    regime: 'REGULAR',
  });

  // Decide alignment form
  const [alignmentForm, setAlignmentForm] = useState({
    agent_id: '',
    pulse_id: '',
    strategy: 'MATCH_PHASE',
    expected_gain: '',
  });

  // Record trend form
  const [trendForm, setTrendForm] = useState({
    agent_id: '',
    cycle_id: '',
    trend: 'STABLE',
    velocity: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveRhythm.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive rhythm stats');
    } finally {
      setLoading(false);
    }
  };

  const loadPulses = async () => {
    try {
      const result = await api.cognitiveRhythm.listPulses();
      const list = Array.isArray(result) ? result : (result?.pulses ?? []);
      setPulses(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load pulses');
    }
  };

  const loadCycles = async () => {
    try {
      const result = await api.cognitiveRhythm.listCycles();
      const list = Array.isArray(result) ? result : (result?.cycles ?? []);
      setCycles(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load cycles');
    }
  };

  const loadAlignments = async () => {
    try {
      const result = await api.cognitiveRhythm.listAlignments();
      const list = Array.isArray(result) ? result : (result?.alignments ?? []);
      setAlignments(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load alignments');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadPulses();
      loadCycles();
      loadAlignments();
    }
  }, [activeSection]);

  const handleRecordPulse = async () => {
    if (!pulseForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: pulseForm.agent_id.trim(),
      phase: pulseForm.phase,
      regime: pulseForm.regime,
    };
    if (pulseForm.intensity.trim()) payload.intensity = Number(pulseForm.intensity);
    try {
      await api.cognitiveRhythm.recordPulse(payload);
      toast.success('Pulse recorded');
      setPulseForm({ agent_id: '', phase: 'FOCUS', intensity: '', regime: 'REGULAR' });
      await loadPulses();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMeasureCycle = async () => {
    if (!cycleForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: cycleForm.agent_id.trim(),
      cycle_type: cycleForm.cycle_type,
      regime: cycleForm.regime,
    };
    if (cycleForm.period.trim()) payload.period = Number(cycleForm.period);
    try {
      await api.cognitiveRhythm.measureCycle(payload);
      toast.success('Cycle measured');
      setCycleForm({ agent_id: '', cycle_type: 'ULTRADIAN', period: '', regime: 'REGULAR' });
      await loadCycles();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDecideAlignment = async () => {
    if (!alignmentForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: alignmentForm.agent_id.trim(),
      strategy: alignmentForm.strategy,
    };
    if (alignmentForm.pulse_id.trim()) payload.pulse_id = alignmentForm.pulse_id.trim();
    if (alignmentForm.expected_gain.trim()) payload.expected_gain = Number(alignmentForm.expected_gain);
    try {
      await api.cognitiveRhythm.decideAlignment(payload);
      toast.success('Alignment decided');
      setAlignmentForm({ agent_id: '', pulse_id: '', strategy: 'MATCH_PHASE', expected_gain: '' });
      await loadAlignments();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordTrend = async () => {
    if (!trendForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: trendForm.agent_id.trim(),
      trend: trendForm.trend,
    };
    if (trendForm.cycle_id.trim()) payload.cycle_id = trendForm.cycle_id.trim();
    if (trendForm.velocity.trim()) payload.velocity = Number(trendForm.velocity);
    try {
      const result = await api.cognitiveRhythm.recordTrend(payload);
      setTrendResult(result);
      toast.success('Trend recorded');
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
          <h2>💓 Cognitive Rhythm</h2>
          <p className="panel-subtitle">Record pulses, measure cycles, and align tasks to cognitive phases</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive rhythm...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💓 Cognitive Rhythm</h2>
        <p className="panel-subtitle">Record pulses, measure cycles, and align tasks to cognitive phases</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_pulses ?? '-'}</span><span className="stat-label">Pulses</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_cycles ?? '-'}</span><span className="stat-label">Cycles</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_alignments ?? '-'}</span><span className="stat-label">Alignments</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_trends ?? '-'}</span><span className="stat-label">Trends</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_rhythm ?? '-'}</span><span className="stat-label">Avg Rhythm</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'pulse', 'alignment'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Rhythm Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Pulses</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_pulses ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Cycles</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_cycles ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Alignments</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_alignments ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Trends</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_trends ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Rhythm</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_rhythm ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Pulses</h3>
            <button onClick={() => loadPulses()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {pulses.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No pulses recorded. Record one in the Pulse section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {pulses.slice(0, 10).map((p: any, i: number) => {
                  const id = p.pulse_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>pulse {id}{p.intensity != null ? ` · intensity: ${p.intensity}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.phase && renderBadge(p.phase, themeColors.secondary)}
                          {p.regime && renderBadge(p.regime, statusColor(p.regime))}
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

      {/* Pulse Section */}
      {activeSection === 'pulse' && (
        <div className="dashboard-section">
          {/* Record Pulse */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Pulse</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={pulseForm.agent_id} onChange={e => setPulseForm({ ...pulseForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Phase</label>
                <select value={pulseForm.phase} onChange={e => setPulseForm({ ...pulseForm, phase: e.target.value })}>
                  {RHYTHM_PHASES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Intensity</label>
                <input value={pulseForm.intensity} onChange={e => setPulseForm({ ...pulseForm, intensity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group">
                <label>Regime</label>
                <select value={pulseForm.regime} onChange={e => setPulseForm({ ...pulseForm, regime: e.target.value })}>
                  {RHYTHM_REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRecordPulse} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Pulse</button>
          </div>

          {/* Measure Cycle */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Measure Cycle</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={cycleForm.agent_id} onChange={e => setCycleForm({ ...cycleForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Cycle Type</label>
                <select value={cycleForm.cycle_type} onChange={e => setCycleForm({ ...cycleForm, cycle_type: e.target.value })}>
                  {CYCLE_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Period</label>
                <input value={cycleForm.period} onChange={e => setCycleForm({ ...cycleForm, period: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 90.0" />
              </div>
              <div className="form-group">
                <label>Regime</label>
                <select value={cycleForm.regime} onChange={e => setCycleForm({ ...cycleForm, regime: e.target.value })}>
                  {RHYTHM_REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleMeasureCycle} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Measure Cycle</button>
          </div>

          {/* Pulses List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>pulse {id}{p.intensity != null ? ` · intensity: ${p.intensity}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.phase && renderBadge(p.phase, themeColors.secondary)}
                          {p.regime && renderBadge(p.regime, statusColor(p.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Cycles List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Cycles ({cycles.length})</h3>
            <button onClick={() => loadCycles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {cycles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No cycles measured. Measure one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {cycles.slice(0, 30).map((c: any, i: number) => {
                  const id = c.cycle_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>cycle {id}{c.period != null ? ` · period: ${c.period}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.cycle_type && renderBadge(c.cycle_type, themeColors.secondary)}
                          {c.regime && renderBadge(c.regime, statusColor(c.regime))}
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

      {/* Alignment Section */}
      {activeSection === 'alignment' && (
        <div className="dashboard-section">
          {/* Decide Alignment */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Decide Alignment</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={alignmentForm.agent_id} onChange={e => setAlignmentForm({ ...alignmentForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Pulse ID</label>
                <input value={alignmentForm.pulse_id} onChange={e => setAlignmentForm({ ...alignmentForm, pulse_id: e.target.value })} placeholder="optional pulse id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={alignmentForm.strategy} onChange={e => setAlignmentForm({ ...alignmentForm, strategy: e.target.value })}>
                  {ALIGNMENT_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Gain</label>
                <input value={alignmentForm.expected_gain} onChange={e => setAlignmentForm({ ...alignmentForm, expected_gain: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
            </div>
            <button onClick={handleDecideAlignment} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Decide Alignment</button>
          </div>

          {/* Record Trend */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Trend</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={trendForm.agent_id} onChange={e => setTrendForm({ ...trendForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Cycle ID</label>
                <input value={trendForm.cycle_id} onChange={e => setTrendForm({ ...trendForm, cycle_id: e.target.value })} placeholder="optional cycle id" />
              </div>
              <div className="form-group">
                <label>Trend</label>
                <select value={trendForm.trend} onChange={e => setTrendForm({ ...trendForm, trend: e.target.value })}>
                  {RHYTHM_TRENDS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Velocity</label>
                <input value={trendForm.velocity} onChange={e => setTrendForm({ ...trendForm, velocity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.3" />
              </div>
            </div>
            <button onClick={handleRecordTrend} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Trend</button>
            {trendResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(trendResult, null, 2)}</pre>
            )}
          </div>

          {/* Alignments List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Alignments ({alignments.length})</h3>
            <button onClick={() => loadAlignments()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {alignments.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No alignments decided. Decide one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {alignments.slice(0, 30).map((a: any, i: number) => {
                  const id = a.alignment_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>alignment {id}{a.pulse_id ? ` · pulse: ${a.pulse_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.strategy && renderBadge(a.strategy, themeColors.secondary)}
                          {a.expected_gain != null && renderBadge(`gain: ${a.expected_gain}`, themeColors.primary)}
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

export default CognitiveRhythmPanel;
