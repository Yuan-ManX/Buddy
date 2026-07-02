import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: sky/blue tones to evoke fluidity, stream, and flow
const themeColors = {
  primary: '#0284c7',
  secondary: '#0ea5e9',
  bg: '#f0f9ff',
  border: '#bae6fd',
  accent: '#e0f2fe',
  text: '#0c4a6e',
};

// Enum values must match backend CognitiveFluidityAxis / FluidityRegime / FluidityBlocker / FlowStrategy / FluidityStage (uppercase).
// AXES represent the different cognitive dimensions that have a fluidity reading.
const AXES = ['REASONING', 'ASSOCIATION', 'EXPRESSION', 'TRANSITION', 'INTEGRATION', 'RESPONSE'];
// REGIMES describe the overall fluidity regime of an agent at a snapshot in time.
const REGIMES = ['CHOKED', 'LABORED', 'SMOOTH', 'FLOWING', 'STREAMING', 'EFFORTLESS'];
// BLOCKERS are impediments that interrupt smooth thought flow.
const BLOCKERS = ['CONFUSION', 'RIGIDITY', 'FATIGUE', 'DOUBT', 'OVERLOAD', 'STUCK'];
// STRATEGIES are interventions an agent can apply to restore or accelerate fluidity.
const STRATEGIES = ['CLEAR', 'EASE', 'GUIDE', 'CHANNEL', 'ACCELERATE', 'RELEASE'];
// STAGES describe the transient phase of a flow cascade as it progresses.
const STAGES = ['STALLED', 'UNCLOGGING', 'GLIDING', 'SURGING', 'CRESTING', 'SETTLING'];

// Map a regime value to a badge color for at-a-glance scanning.
const REGIME_COLORS: Record<string, string> = {
  CHOKED: '#7f1d1d',
  LABORED: '#b91c1c',
  SMOOTH: '#0284c7',
  FLOWING: '#0ea5e9',
  STREAMING: '#38bdf8',
  EFFORTLESS: '#7dd3fc',
};

// Map a stage value to a badge color for cascade phase visualization.
const STAGE_COLORS: Record<string, string> = {
  STALLED: '#6b7280',
  UNCLOGGING: '#f59e0b',
  GLIDING: '#0ea5e9',
  SURGING: '#0284c7',
  CRESTING: '#0369a1',
  SETTLING: '#22c55e',
};

export const CognitiveFluidityPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Section tab state. 'overview' shows a dashboard summary; the others expose the matching create + list UI.
  const [activeSection, setActiveSection] = useState<'overview' | 'readings' | 'stutters' | 'snapshots' | 'plans' | 'cascades'>('overview');

  // Top-level collections that back the lists shown in each section and the overview.
  const [readings, setReadings] = useState<any[]>([]);
  const [stutters, setStutters] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [cascades, setCascades] = useState<any[]>([]);

  // The most recent snapshot response, kept for inline display after a "take snapshot" call.
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Form state for the record-reading flow.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'REASONING',
    fluidity_score: '',
    resistance: '',
    notes: '',
  });

  // Form state for the record-stutter flow.
  const [stutterForm, setStutterForm] = useState({
    agent_id: '',
    axis: 'REASONING',
    blocker: 'CONFUSION',
    severity: '',
    duration_ms: '',
    notes: '',
  });

  // Form state for the take-snapshot flow.
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Form state for the plan-flow flow.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    axis: 'REASONING',
    strategy: 'CLEAR',
    target_score: '',
    rationale: '',
  });

  // Form state for the record-cascade flow.
  const [cascadeForm, setCascadeForm] = useState({
    agent_id: '',
    stage: 'STALLED',
    axis: 'REASONING',
    depth: '',
    notes: '',
  });

  // Fetch the aggregate stats counters for the top stats bar.
  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveFluidity.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive fluidity stats');
    } finally {
      setLoading(false);
    }
  };

  // Load the readings list. API may return either a bare array or a wrapped {readings: ...} object.
  const loadReadings = async () => {
    try {
      const result = await api.cognitiveFluidity.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  // Load the stutters list. Same unwrapping rule as readings.
  const loadStutters = async () => {
    try {
      const result = await api.cognitiveFluidity.listStutters();
      const list = Array.isArray(result) ? result : (result?.stutters ?? []);
      setStutters(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load stutters');
    }
  };

  // Load the snapshots list. Snapshots capture a moment-in-time fluidity state for an agent.
  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveFluidity.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  // Load the plans list. Plans describe interventions to restore or improve fluidity.
  const loadPlans = async () => {
    try {
      const result = await api.cognitiveFluidity.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Load the cascades list. Cascades track the trajectory of a single flow episode.
  const loadCascades = async () => {
    try {
      const result = await api.cognitiveFluidity.listCascades();
      const list = Array.isArray(result) ? result : (result?.cascades ?? []);
      setCascades(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load cascades');
    }
  };

  // Initial stats load on mount.
  useEffect(() => { loadStats(); }, []);

  // Reload everything when the user returns to the overview tab.
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadStutters();
      loadSnapshots();
      loadPlans();
      loadCascades();
    }
  }, [activeSection]);

  // Submit a new fluidity reading. Numeric inputs default to 0.5 / 0 when blank to keep the API happy.
  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      fluidity_score: readingForm.fluidity_score.trim() === '' ? 0.5 : Number(readingForm.fluidity_score),
      resistance: readingForm.resistance.trim() === '' ? 0 : Number(readingForm.resistance),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveFluidity.recordReading(payload);
      toast.success('Reading recorded');
      // Reset the form to a clean default state.
      setReadingForm({ agent_id: '', axis: 'REASONING', fluidity_score: '', resistance: '', notes: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  // Submit a new stutter event. Stutters are short-lived interruptions to flow.
  const handleRecordStutter = async () => {
    if (!stutterForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: stutterForm.agent_id.trim(),
      axis: stutterForm.axis,
      blocker: stutterForm.blocker,
      severity: stutterForm.severity.trim() === '' ? 0.5 : Number(stutterForm.severity),
      duration_ms: stutterForm.duration_ms.trim() === '' ? 0 : Number(stutterForm.duration_ms),
    };
    if (stutterForm.notes) payload.notes = stutterForm.notes.trim();
    try {
      await api.cognitiveFluidity.recordStutter(payload);
      toast.success('Stutter recorded');
      setStutterForm({ agent_id: '', axis: 'REASONING', blocker: 'CONFUSION', severity: '', duration_ms: '', notes: '' });
      await loadStutters();
    } catch (e: any) { toast.error(e.message); }
  };

  // Capture a snapshot of the current fluidity state for the given agent. The response is shown inline.
  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveFluidity.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  // Submit a flow-improvement plan that maps a strategy to a target fluidity score on a specific axis.
  const handlePlanFlow = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      axis: planForm.axis,
      strategy: planForm.strategy,
      target_score: planForm.target_score.trim() === '' ? 0 : Number(planForm.target_score),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveFluidity.planFlow(payload);
      toast.success('Flow plan created');
      setPlanForm({ agent_id: '', axis: 'REASONING', strategy: 'CLEAR', target_score: '', rationale: '' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  // Record a new cascade event to track progression of a flow episode through its stages.
  const handleRecordCascade = async () => {
    if (!cascadeForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: cascadeForm.agent_id.trim(),
      stage: cascadeForm.stage,
      axis: cascadeForm.axis,
      depth: cascadeForm.depth.trim() === '' ? 0 : Number(cascadeForm.depth),
    };
    if (cascadeForm.notes) payload.notes = cascadeForm.notes.trim();
    try {
      await api.cognitiveFluidity.recordCascade(payload);
      toast.success('Cascade recorded');
      setCascadeForm({ agent_id: '', stage: 'STALLED', axis: 'REASONING', depth: '', notes: '' });
      await loadCascades();
    } catch (e: any) { toast.error(e.message); }
  };

  // Small colored pill used to tag values inline.
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

  // Helper to resolve the badge color for a regime value, falling back to the primary theme color.
  const regimeColor = (s: string) => REGIME_COLORS[s] ?? themeColors.primary;
  // Helper to resolve the badge color for a stage value.
  const stageColor = (s: string) => STAGE_COLORS[s] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🌊 Cognitive Fluidity</h2>
          <p className="panel-subtitle">Track fluidity readings, capture stutters, snapshot flow state, plan interventions, and follow cascade trajectories</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive fluidity...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌊 Cognitive Fluidity</h2>
        <p className="panel-subtitle">Track fluidity readings, capture stutters, snapshot flow state, plan interventions, and follow cascade trajectories</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_stutters ?? '-'}</span><span className="stat-label">Stutters</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_cascades ?? '-'}</span><span className="stat-label">Cascades</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'stutters', 'snapshots', 'plans', 'cascades'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Fluidity Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Stutters</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_stutters ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Cascades</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_cascades ?? 0}</div>
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
                          {typeof r.fluidity_score !== 'undefined' && renderBadge(`flow ${r.fluidity_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Stutters</h3>
            <button onClick={() => loadStutters()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {stutters.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No stutters recorded. Record one in the Stutters section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {stutters.slice(0, 10).map((s: any, i: number) => {
                  const id = s.stutter_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>stutter {id}{s.axis ? ` · ${s.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.blocker && renderBadge(s.blocker, '#b91c1c')}
                          {typeof s.severity !== 'undefined' && renderBadge(`sev ${s.severity}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Cascades</h3>
            <button onClick={() => loadCascades()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {cascades.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No cascades recorded. Record one in the Cascades section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {cascades.slice(0, 10).map((c: any, i: number) => {
                  const id = c.cascade_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>cascade {id}{c.axis ? ` · ${c.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.stage && renderBadge(c.stage, stageColor(c.stage))}
                          {typeof c.depth !== 'undefined' && renderBadge(`depth ${c.depth}`, themeColors.secondary)}
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
                <label>Axis</label>
                <select className="form-select" value={readingForm.axis} onChange={e => setReadingForm({ ...readingForm, axis: e.target.value })}>
                  {AXES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Fluidity Score</label>
                <input className="form-input" value={readingForm.fluidity_score} onChange={e => setReadingForm({ ...readingForm, fluidity_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group">
                <label>Resistance</label>
                <input className="form-input" value={readingForm.resistance} onChange={e => setReadingForm({ ...readingForm, resistance: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.2" />
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.axis ? ` · ${r.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {typeof r.fluidity_score !== 'undefined' && renderBadge(`flow ${r.fluidity_score}`, themeColors.primary)}
                          {typeof r.resistance !== 'undefined' && renderBadge(`resist ${r.resistance}`, themeColors.secondary)}
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

      {/* Stutters Section */}
      {activeSection === 'stutters' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Stutter</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={stutterForm.agent_id} onChange={e => setStutterForm({ ...stutterForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={stutterForm.axis} onChange={e => setStutterForm({ ...stutterForm, axis: e.target.value })}>
                  {AXES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Blocker</label>
                <select className="form-select" value={stutterForm.blocker} onChange={e => setStutterForm({ ...stutterForm, blocker: e.target.value })}>
                  {BLOCKERS.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Severity</label>
                <input className="form-input" value={stutterForm.severity} onChange={e => setStutterForm({ ...stutterForm, severity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>Duration (ms)</label>
                <input className="form-input" value={stutterForm.duration_ms} onChange={e => setStutterForm({ ...stutterForm, duration_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 1500" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={stutterForm.notes} onChange={e => setStutterForm({ ...stutterForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordStutter} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Stutter</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Stutters ({stutters.length})</h3>
            <button onClick={() => loadStutters()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {stutters.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No stutters recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {stutters.slice(0, 30).map((s: any, i: number) => {
                  const id = s.stutter_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>stutter {id}{s.axis ? ` · ${s.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.blocker && renderBadge(s.blocker, '#b91c1c')}
                          {typeof s.severity !== 'undefined' && renderBadge(`sev ${s.severity}`, themeColors.primary)}
                          {typeof s.duration_ms !== 'undefined' && renderBadge(`${s.duration_ms}ms`, themeColors.secondary)}
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
                          {s.regime && renderBadge(s.regime, regimeColor(s.regime))}
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
            <h3 style={{ color: themeColors.text }}>Plan Flow</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={planForm.axis} onChange={e => setPlanForm({ ...planForm, axis: e.target.value })}>
                  {AXES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Score</label>
                <input className="form-input" value={planForm.target_score} onChange={e => setPlanForm({ ...planForm, target_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.85" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for plan" />
              </div>
            </div>
            <button onClick={handlePlanFlow} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Flow</button>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>plan {id}{p.axis ? ` · ${p.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.strategy && renderBadge(p.strategy, themeColors.secondary)}
                          {typeof p.target_score !== 'undefined' && renderBadge(`target ${p.target_score}`, themeColors.primary)}
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

      {/* Cascades Section */}
      {activeSection === 'cascades' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Cascade</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={cascadeForm.agent_id} onChange={e => setCascadeForm({ ...cascadeForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Stage</label>
                <select className="form-select" value={cascadeForm.stage} onChange={e => setCascadeForm({ ...cascadeForm, stage: e.target.value })}>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={cascadeForm.axis} onChange={e => setCascadeForm({ ...cascadeForm, axis: e.target.value })}>
                  {AXES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Depth</label>
                <input className="form-input" value={cascadeForm.depth} onChange={e => setCascadeForm({ ...cascadeForm, depth: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 3" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={cascadeForm.notes} onChange={e => setCascadeForm({ ...cascadeForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordCascade} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Cascade</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Cascades ({cascades.length})</h3>
            <button onClick={() => loadCascades()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {cascades.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No cascades recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {cascades.slice(0, 30).map((c: any, i: number) => {
                  const id = c.cascade_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>cascade {id}{c.axis ? ` · ${c.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.stage && renderBadge(c.stage, stageColor(c.stage))}
                          {typeof c.depth !== 'undefined' && renderBadge(`depth ${c.depth}`, themeColors.secondary)}
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

export default CognitiveFluidityPanel;
