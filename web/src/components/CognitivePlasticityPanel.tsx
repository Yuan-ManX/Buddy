import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: indigo/purple for cognitive plasticity.
// Plasticity concerns how readily a cognitive structure can be reshaped, so we use
// a cool, transformative indigo/purple palette to evoke metamorphic potential.
const themeColors = {
  primary: '#4f46e5',    // indigo-600: main interactive accent
  secondary: '#7c3aed',  // violet-600: secondary accent
  bg: '#eef2ff',         // indigo-50: panel surface
  border: '#c7d2fe',     // indigo-200: dividers
  accent: '#e0e7ff',     // indigo-100: subtle highlights
  text: '#312e81',       // indigo-900: readable text on light backgrounds
};

// Enum values must match the backend PlasticityAxis / PlasticityRegime /
// PlasticityTrigger / ReshapeStrategy / PlasticityStage definitions exactly
// (uppercase). Keeping these in sync with the backend is critical, because the
// API validates incoming payloads against the server-side enums.
const AXES = ['MORPHOLOGICAL', 'ASSOCIATIVE', 'PROCEDURAL', 'EPISTEMIC', 'AFFECTIVE', 'NORMATIVE'];
const REGIMES = ['RIGID', 'SET', 'YIELDING', 'MALLEABLE', 'ADAPTIVE', 'TRANSFORMABLE'];
const TRIGGERS = ['EXPERIENCE', 'INSTRUCTION', 'REFLECTION', 'SURPRISE', 'FATIGUE', 'INSIGHT'];
const STRATEGIES = ['REINFORCE', 'EXTEND', 'RECOMBINE', 'PRUNE', 'RECONFIGURE', 'OVERWRITE'];
const STAGES = ['FROZEN', 'CRACKED', 'BENDING', 'REFORMING', 'SETTLING', 'STABLE'];

// Map a plasticity regime to a badge color for at-a-glance scanning in lists
// and the overview. Cooler tones map to more rigid regimes, warmer/bright
// tones map to highly plastic regimes.
const REGIME_COLORS: Record<string, string> = {
  RIGID: '#475569',        // slate-600: low plasticity
  SET: '#1e40af',          // blue-800: barely yielding
  YIELDING: '#2563eb',     // blue-600: starting to flex
  MALLEABLE: '#7c3aed',    // violet-600: easily shaped
  ADAPTIVE: '#a855f7',     // purple-500: actively adapting
  TRANSFORMABLE: '#ec4899',// pink-500: fully transformable
};

// Map a plasticity stage to a badge color. Stages describe the temporal phase
// of an ongoing reshape, so colors progress from "cold/inert" to "warm/stable".
const STAGE_COLORS: Record<string, string> = {
  FROZEN: '#0f172a',       // slate-900: completely frozen
  CRACKED: '#7c2d12',      // orange-900: starting to break
  BENDING: '#c2410c',      // orange-700: mid-process
  REFORMING: '#7c3aed',    // violet-600: restructuring
  SETTLING: '#2563eb',     // blue-600: cooling down
  STABLE: '#16a34a',       // green-600: settled
};

export const CognitivePlasticityPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // The active section controls which subsection of the panel is rendered. We
  // intentionally use a string union to keep tab state in lock-step with the
  // tabs we render below.
  const [activeSection, setActiveSection] = useState<'overview' | 'readings' | 'reshapes' | 'snapshots' | 'plans' | 'settles'>('overview');

  // Backing state for the five record types exposed by the plasticity engine.
  // Each list is populated when its tab is visited and refreshed by the user.
  const [readings, setReadings] = useState<any[]>([]);
  const [reshapes, setReshapes] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [settles, setSettles] = useState<any[]>([]);
  // After taking a snapshot, we keep the immediate response around so the user
  // can inspect the freshly captured plasticity profile.
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form: captures an instantaneous plasticity reading for an
  // agent along one of the six axes, with a regime classification.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'MORPHOLOGICAL',
    score: '',
    regime: 'RIGID',
    trigger: 'EXPERIENCE',
    intensity: '',
    notes: '',
  });

  // Record reshape form: describes a discrete reshaping event applied to an
  // agent's cognitive structure using one of the six strategies.
  const [reshapeForm, setReshapeForm] = useState({
    agent_id: '',
    axis: 'MORPHOLOGICAL',
    strategy: 'REINFORCE',
    magnitude: '',
    stage: 'FROZEN',
    notes: '',
  });

  // Take snapshot form: snapshots take only an agent id; the server figures
  // out the rest by sampling the agent's current plasticity profile.
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan reshape form: capture a planned reshaping intervention, including
  // the desired end-state score and a free-form rationale.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'REINFORCE',
    target_score: '',
    rationale: '',
  });

  // Record settle form: log the completion of a reshape by recording the
  // from->to stage transition and the residual instability remaining.
  const [settleForm, setSettleForm] = useState({
    agent_id: '',
    axis: 'MORPHOLOGICAL',
    from_stage: 'FROZEN',
    to_stage: 'STABLE',
    duration_ms: '',
    residual_instability: '',
    notes: '',
  });

  // --- Loaders -------------------------------------------------------------
  // Each loader normalizes the backend's response shape, since the engine may
  // return either a bare array or an object containing the array under a
  // conventional key (e.g. `{ readings: [...] }`). This keeps the UI robust to
  // either encoding.

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitivePlasticity.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive plasticity stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitivePlasticity.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadReshapes = async () => {
    try {
      const result = await api.cognitivePlasticity.listReshapes();
      const list = Array.isArray(result) ? result : (result?.reshapes ?? []);
      setReshapes(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load reshapes');
    }
  };

  const loadSnapshots = async () => {
    try {
      const result = await api.cognitivePlasticity.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitivePlasticity.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  const loadSettles = async () => {
    try {
      const result = await api.cognitivePlasticity.listSettles();
      const list = Array.isArray(result) ? result : (result?.settles ?? []);
      setSettles(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load settles');
    }
  };

  // Initial load: fetch stats on mount so the header reflects engine state
  // even before the user navigates away from the overview tab.
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview so the dashboard always
  // reflects the freshest data the user has permission to see.
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadReshapes();
      loadSnapshots();
      loadPlans();
      loadSettles();
    }
  }, [activeSection]);

  // --- Submission handlers -------------------------------------------------
  // Each handler validates the required inputs, constructs a payload with the
  // shapes the backend expects, posts it, and then refreshes the local list.
  // Numeric fields default sensibly to 0 / 0.5 to avoid backend validation
  // errors when the user leaves them blank.

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      score: readingForm.score.trim() === '' ? 0.5 : Number(readingForm.score),
      regime: readingForm.regime,
      trigger: readingForm.trigger,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitivePlasticity.recordReading(payload);
      toast.success('Reading recorded');
      // Reset the form to a clean default after a successful submission.
      setReadingForm({ agent_id: '', axis: 'MORPHOLOGICAL', score: '', regime: 'RIGID', trigger: 'EXPERIENCE', intensity: '', notes: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordReshape = async () => {
    if (!reshapeForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: reshapeForm.agent_id.trim(),
      axis: reshapeForm.axis,
      strategy: reshapeForm.strategy,
      magnitude: reshapeForm.magnitude.trim() === '' ? 0 : Number(reshapeForm.magnitude),
      stage: reshapeForm.stage,
    };
    if (reshapeForm.notes) payload.notes = reshapeForm.notes.trim();
    try {
      await api.cognitivePlasticity.recordReshape(payload);
      toast.success('Reshape recorded');
      setReshapeForm({ agent_id: '', axis: 'MORPHOLOGICAL', strategy: 'REINFORCE', magnitude: '', stage: 'FROZEN', notes: '' });
      await loadReshapes();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      const result = await api.cognitivePlasticity.takeSnapshot({ agent_id: snapshotForm.agent_id.trim() });
      // Keep the immediate response around so the user can see the freshly
      // captured plasticity profile before navigating away.
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanReshape = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_score: planForm.target_score.trim() === '' ? 0 : Number(planForm.target_score),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitivePlasticity.planReshape(payload);
      toast.success('Reshape plan created');
      setPlanForm({ agent_id: '', strategy: 'REINFORCE', target_score: '', rationale: '' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordSettle = async () => {
    if (!settleForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: settleForm.agent_id.trim(),
      axis: settleForm.axis,
      from_stage: settleForm.from_stage,
      to_stage: settleForm.to_stage,
      duration_ms: settleForm.duration_ms.trim() === '' ? 0 : Number(settleForm.duration_ms),
      residual_instability: settleForm.residual_instability.trim() === '' ? 0 : Number(settleForm.residual_instability),
    };
    if (settleForm.notes) payload.notes = settleForm.notes.trim();
    try {
      await api.cognitivePlasticity.recordSettle(payload);
      toast.success('Settle recorded');
      setSettleForm({ agent_id: '', axis: 'MORPHOLOGICAL', from_stage: 'FROZEN', to_stage: 'STABLE', duration_ms: '', residual_instability: '', notes: '' });
      await loadSettles();
    } catch (e: any) { toast.error(e.message); }
  };

  // --- Helpers -------------------------------------------------------------
  // Small visual primitive used by every list to render categorical tags
  // (axis, regime, strategy, etc.) in a consistent pill style.
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

  // Resolve a regime label to its badge color, falling back to the panel
  // primary if we encounter an unknown value (e.g. from a newer backend).
  const regimeColor = (r: string) => REGIME_COLORS[r] ?? themeColors.primary;
  // Resolve a stage label to its badge color in the same way.
  const stageColor = (s: string) => STAGE_COLORS[s] ?? themeColors.primary;

  // Loading state: render a lightweight header + spinner to keep the panel
  // layout stable while the first stats request is in flight.
  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🌊 Cognitive Plasticity</h2>
          <p className="panel-subtitle">Measure plasticity, record reshapes, and plan structural changes across the cognitive plasticity engine</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive plasticity...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌊 Cognitive Plasticity</h2>
        <p className="panel-subtitle">Measure plasticity, record reshapes, and plan structural changes across the cognitive plasticity engine</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar: a compact at-a-glance summary of plasticity engine state. */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_reshapes ?? '-'}</span><span className="stat-label">Reshapes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_score ?? '-'}</span><span className="stat-label">Avg Score</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs: simple pill-style buttons that swap the rendered
          section. The active tab is highlighted using the panel's primary
          color so the user always knows where they are. */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'reshapes', 'snapshots', 'plans', 'settles'] as const).map(s => (
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

      {/* Overview Section: dashboard-style summary. Combines aggregate stats
          with the most recent few records of each type. This is the default
          landing tab and is intended to convey the engine's state at a glance. */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plasticity Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Reshapes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_reshapes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Score</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_score ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dominant Regime</div>
                <div style={{ fontSize: 18, color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</div>
              </div>
            </div>
          </div>

          {/* Regime counts: a horizontal mini-distribution of how many agents
              currently sit in each plasticity regime. Helpful for spotting
              skewed populations (e.g. everyone is RIGID). */}
          {stats.regime_counts && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Regime Distribution</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8, marginTop: 12 }}>
                {REGIMES.map(r => {
                  const count = stats.regime_counts?.[r] ?? 0;
                  return (
                    <div key={r} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: themeColors.text, opacity: 0.7 }}>{r}</div>
                      <div style={{ fontSize: 20, fontWeight: 700, color: regimeColor(r) }}>{count}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Recent Readings: short, most-recent-first list. Each entry is
              rendered with axis, regime, trigger and score badges so the user
              can scan the latest plasticity state at a glance. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Readings</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one in the Readings section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 10).map((r: any, i: number) => {
                  // Prefer the canonical reading_id from the backend, then
                  // fall back to id or index for resilience.
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
                          {r.regime && renderBadge(r.regime, regimeColor(r.regime))}
                          {r.trigger && renderBadge(r.trigger, themeColors.primary)}
                          {typeof r.score !== 'undefined' && renderBadge(`score ${r.score}`, themeColors.secondary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent Reshapes: show the most recent interventions so the user
              can verify that the engine is actually mutating its state. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Reshapes</h3>
            <button onClick={() => loadReshapes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {reshapes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No reshapes recorded. Record one in the Reshapes section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {reshapes.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reshape_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reshape {id}{r.axis ? ` · ${r.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.strategy && renderBadge(r.strategy, themeColors.primary)}
                          {r.stage && renderBadge(r.stage, stageColor(r.stage))}
                          {typeof r.magnitude !== 'undefined' && renderBadge(`mag ${r.magnitude}`, themeColors.secondary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent Settles: surfaces how recent reshapes have concluded, so
              operators can see whether the engine is converging to STABLE. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Settles</h3>
            <button onClick={() => loadSettles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {settles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No settles recorded. Record one in the Settles section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {settles.slice(0, 10).map((s: any, i: number) => {
                  const id = s.settle_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>settle {id}{s.axis ? ` · ${s.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.from_stage && s.to_stage && renderBadge(`${s.from_stage}->${s.to_stage}`, stageColor(s.to_stage))}
                          {typeof s.duration_ms !== 'undefined' && renderBadge(`${s.duration_ms}ms`, themeColors.primary)}
                          {typeof s.residual_instability !== 'undefined' && renderBadge(`residual ${s.residual_instability}`, themeColors.secondary)}
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

      {/* Readings Section: dedicated view for browsing and creating plasticity
          readings. Mirrors the structure used in the other cognitive panels. */}
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
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Regime</label>
                <select className="form-select" value={readingForm.regime} onChange={e => setReadingForm({ ...readingForm, regime: e.target.value })}>
                  {REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Trigger</label>
                <select className="form-select" value={readingForm.trigger} onChange={e => setReadingForm({ ...readingForm, trigger: e.target.value })}>
                  {TRIGGERS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Score</label>
                <input className="form-input" value={readingForm.score} onChange={e => setReadingForm({ ...readingForm, score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.65" />
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
                          {r.regime && renderBadge(r.regime, regimeColor(r.regime))}
                          {r.trigger && renderBadge(r.trigger, themeColors.primary)}
                          {typeof r.score !== 'undefined' && renderBadge(`score ${r.score}`, themeColors.secondary)}
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

      {/* Reshapes Section: capture discrete structural changes applied to an
          agent. Each reshape selects an axis, a strategy, and an initial
          stage in the reshape lifecycle. */}
      {activeSection === 'reshapes' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reshape</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={reshapeForm.agent_id} onChange={e => setReshapeForm({ ...reshapeForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={reshapeForm.axis} onChange={e => setReshapeForm({ ...reshapeForm, axis: e.target.value })}>
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={reshapeForm.strategy} onChange={e => setReshapeForm({ ...reshapeForm, strategy: e.target.value })}>
                  {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Stage</label>
                <select className="form-select" value={reshapeForm.stage} onChange={e => setReshapeForm({ ...reshapeForm, stage: e.target.value })}>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Magnitude</label>
                <input className="form-input" value={reshapeForm.magnitude} onChange={e => setReshapeForm({ ...reshapeForm, magnitude: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={reshapeForm.notes} onChange={e => setReshapeForm({ ...reshapeForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordReshape} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reshape</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Reshapes ({reshapes.length})</h3>
            <button onClick={() => loadReshapes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {reshapes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No reshapes recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {reshapes.slice(0, 30).map((r: any, i: number) => {
                  const id = r.reshape_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reshape {id}{r.axis ? ` · ${r.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.strategy && renderBadge(r.strategy, themeColors.primary)}
                          {r.stage && renderBadge(r.stage, stageColor(r.stage))}
                          {typeof r.magnitude !== 'undefined' && renderBadge(`mag ${r.magnitude}`, themeColors.secondary)}
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

      {/* Snapshots Section: capture a point-in-time plasticity profile for
          an agent. The server computes regime counts and the immediate
          response is echoed back to the user for inspection. */}
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
                          {typeof s.score !== 'undefined' && renderBadge(`score ${s.score}`, themeColors.secondary)}
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

      {/* Plans Section: stage a future reshape intervention. A plan describes
          the desired end-state, the strategy to use, and a free-form
          rationale for the operator to recall intent later. */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Reshape</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Score</label>
                <input className="form-input" value={planForm.target_score} onChange={e => setPlanForm({ ...planForm, target_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for plan" />
              </div>
            </div>
            <button onClick={handlePlanReshape} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Reshape</button>
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

      {/* Settles Section: log a stage transition once a reshape concludes.
          This is the closing record of a reshape lifecycle, capturing how long
          it took and how much instability remained at the new stage. */}
      {activeSection === 'settles' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Settle</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={settleForm.agent_id} onChange={e => setSettleForm({ ...settleForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={settleForm.axis} onChange={e => setSettleForm({ ...settleForm, axis: e.target.value })}>
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>From Stage</label>
                <select className="form-select" value={settleForm.from_stage} onChange={e => setSettleForm({ ...settleForm, from_stage: e.target.value })}>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Stage</label>
                <select className="form-select" value={settleForm.to_stage} onChange={e => setSettleForm({ ...settleForm, to_stage: e.target.value })}>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Duration (ms)</label>
                <input className="form-input" value={settleForm.duration_ms} onChange={e => setSettleForm({ ...settleForm, duration_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 1500" />
              </div>
              <div className="form-group">
                <label>Residual Instability</label>
                <input className="form-input" value={settleForm.residual_instability} onChange={e => setSettleForm({ ...settleForm, residual_instability: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={settleForm.notes} onChange={e => setSettleForm({ ...settleForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordSettle} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Settle</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Settles ({settles.length})</h3>
            <button onClick={() => loadSettles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {settles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No settles recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {settles.slice(0, 30).map((s: any, i: number) => {
                  const id = s.settle_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>settle {id}{s.axis ? ` · ${s.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.from_stage && s.to_stage && renderBadge(`${s.from_stage}->${s.to_stage}`, stageColor(s.to_stage))}
                          {typeof s.duration_ms !== 'undefined' && renderBadge(`${s.duration_ms}ms`, themeColors.primary)}
                          {typeof s.residual_instability !== 'undefined' && renderBadge(`residual ${s.residual_instability}`, themeColors.secondary)}
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

export default CognitivePlasticityPanel;
