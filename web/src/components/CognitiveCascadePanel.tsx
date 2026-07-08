// CognitiveCascadePanel: a React TypeScript panel for the cognitive cascade engine.
//
// This panel allows operators to:
//   - View aggregate stats about cognitive cascade across the system.
//   - Record cascade readings for agents (axis / cascade score / source).
//   - Record flows (events that shift the cascade of an axis).
//   - Take snapshots of an agent's current cascade state.
//   - Plan flow strategies to deliberately shape the cascade profile of an agent.
//   - Record tier transitions (terminal / locked-in cascade stage transitions).
//
// The visual style is amber to match the "cascade" theme (flowing / pooling water).

import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: amber tones for cognitive cascade (flowing / pooling feel).
const themeColors = {
  primary: '#d97706',
  secondary: '#f59e0b',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

// Enum values must match the backend's CascadeAxis / CascadeRegime /
// CascadeSource / CascadeStrategy / CascadeStage enums exactly
// (uppercase strings).
const AXES = ['TIER', 'LAYER', 'STREAM', 'FALL', 'POOL', 'DRAIN'];
const REGIMES = ['DRY', 'TRICKLE', 'FLOWING', 'CASCADING', 'TORRENT', 'FLOOD'];
const SOURCES = ['GRAVITY', 'PRESSURE', 'VOLUME', 'CHANNEL', 'SLOPE', 'OBSTRUCTION'];
const STRATEGIES = ['ROUTE', 'ACCELERATE', 'POOL', 'DIVERT', 'MERGE', 'RELEASE'];
const STAGES = ['SOURCE', 'TRICKLING', 'FALLING', 'CASCADING', 'POOLED', 'OVERFLOW'];

// Map a regime value to a badge color so a glance tells you how cascaded the agent is.
const REGIME_COLORS: Record<string, string> = {
  DRY: '#1f2937',
  TRICKLE: '#6b7280',
  FLOWING: '#f59e0b',
  CASCADING: '#d97706',
  TORRENT: '#b45309',
  FLOOD: '#78350f',
};

// Map a stage value to a badge color for the tier transition process.
const STAGE_COLORS: Record<string, string> = {
  SOURCE: '#1f2937',
  TRICKLING: '#6b7280',
  FALLING: '#f59e0b',
  CASCADING: '#d97706',
  POOLED: '#b45309',
  OVERFLOW: '#78350f',
};

export const CognitiveCascadePanel: React.FC = () => {
  // Toast helper for success / error notifications.
  const toast = useToast();

  // Top-level stats object loaded once on mount.
  const [stats, setStats] = useState<any>(null);
  // Loading flag for the initial stats fetch.
  const [loading, setLoading] = useState(true);
  // Top-level error message for the stats bar.
  const [error, setError] = useState<string | null>(null);

  // The currently active section tab.
  const [activeSection, setActiveSection] = useState<
    'overview' | 'readings' | 'flows' | 'snapshots' | 'plans' | 'transitions'
  >('overview');

  // Per-section data lists, populated lazily.
  const [readings, setReadings] = useState<any[]>([]);
  const [flows, setFlows] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [transitions, setTransitions] = useState<any[]>([]);
  // Stores the most recent snapshot returned from the backend (for inline JSON display).
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form state.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'TIER',
    cascade_score: '',
    source: 'GRAVITY',
    intensity: '',
    notes: '',
  });

  // Record flow form state.
  const [flowForm, setFlowForm] = useState({
    agent_id: '',
    axis: 'TIER',
    source: 'GRAVITY',
    before_score: '',
    after_score: '',
    flow_magnitude: '',
    notes: '',
  });

  // Take snapshot form state (just an agent id).
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan flow form state.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'ROUTE',
    target_cascade: '',
    rationale: '',
  });

  // Record tier transition form state (no notes field on this record type).
  const [transitionForm, setTransitionForm] = useState({
    agent_id: '',
    from_stage: 'SOURCE',
    to_stage: 'TRICKLING',
    interval_ms: '',
    signature: '',
  });

  // --- Loaders ---
  // Each loader is defensive: it accepts either an array, or an object that wraps
  // the array in a property (e.g. `{ readings: [...] }`). This tolerates both
  // paginated and unpaginated backend responses.

  // Fetch the global cascade stats object.
  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveCascade.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive cascade stats');
    } finally {
      setLoading(false);
    }
  };

  // Fetch the list of all cascade readings.
  const loadReadings = async () => {
    try {
      const result = await api.cognitiveCascade.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? result?.items ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  // Fetch the list of all flow events.
  const loadFlows = async () => {
    try {
      const result = await api.cognitiveCascade.listFlows();
      const list = Array.isArray(result) ? result : (result?.flows ?? result?.items ?? []);
      setFlows(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load flows');
    }
  };

  // Fetch the list of all snapshots.
  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveCascade.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? result?.items ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  // Fetch the list of all flow plans.
  const loadPlans = async () => {
    try {
      const result = await api.cognitiveCascade.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? result?.items ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Fetch the list of all tier transition events.
  const loadTransitions = async () => {
    try {
      const result = await api.cognitiveCascade.listTierTransitions();
      const list = Array.isArray(result) ? result : (result?.transitions ?? result?.items ?? []);
      setTransitions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load transitions');
    }
  };

  // Initial load: pull stats once on mount.
  useEffect(() => { loadStats(); }, []);

  // Reload stats + per-section lists when the user enters the overview tab.
  // This keeps the overview fresh and lets the user verify counts without
  // having to click into each sub-section first.
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadFlows();
      loadSnapshots();
      loadPlans();
      loadTransitions();
    }
  }, [activeSection]);

  // --- Handlers ---

  // Submit a new cascade reading.
  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    // Build the payload, applying sensible defaults for empty numeric inputs.
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      cascade_score: readingForm.cascade_score.trim() === '' ? 0.5 : Number(readingForm.cascade_score),
      source: readingForm.source,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveCascade.recordReading(payload);
      toast.success('Reading recorded');
      // Reset the form to a clean default state.
      setReadingForm({
        agent_id: '',
        axis: 'TIER',
        cascade_score: '',
        source: 'GRAVITY',
        intensity: '',
        notes: '',
      });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  // Submit a new flow event.
  const handleRecordFlow = async () => {
    if (!flowForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: flowForm.agent_id.trim(),
      axis: flowForm.axis,
      source: flowForm.source,
      before_score: flowForm.before_score.trim() === '' ? 0.5 : Number(flowForm.before_score),
      after_score: flowForm.after_score.trim() === '' ? 0.5 : Number(flowForm.after_score),
      flow_magnitude: flowForm.flow_magnitude.trim() === '' ? 0 : Number(flowForm.flow_magnitude),
    };
    if (flowForm.notes) payload.notes = flowForm.notes.trim();
    try {
      await api.cognitiveCascade.recordFlow(payload);
      toast.success('Flow recorded');
      setFlowForm({
        agent_id: '',
        axis: 'TIER',
        source: 'GRAVITY',
        before_score: '',
        after_score: '',
        flow_magnitude: '',
        notes: '',
      });
      await loadFlows();
    } catch (e: any) { toast.error(e.message); }
  };

  // Take a new cascade snapshot for the given agent.
  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveCascade.takeSnapshot(payload);
      // Surface the raw response inline so the operator can see what was captured.
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  // Create a new flow plan for an agent.
  const handlePlanFlow = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_cascade: planForm.target_cascade.trim() === '' ? 0 : Number(planForm.target_cascade),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveCascade.planFlow(payload);
      toast.success('Flow plan created');
      setPlanForm({
        agent_id: '',
        strategy: 'ROUTE',
        target_cascade: '',
        rationale: '',
      });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  // Record a tier transition (final cascade stage transition) event.
  // Note: tier transition records do not accept a notes field on the backend.
  const handleRecordTransition = async () => {
    if (!transitionForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: transitionForm.agent_id.trim(),
      from_stage: transitionForm.from_stage,
      to_stage: transitionForm.to_stage,
      interval_ms: transitionForm.interval_ms.trim() === '' ? 0 : Number(transitionForm.interval_ms),
      signature: transitionForm.signature.trim(),
    };
    try {
      await api.cognitiveCascade.recordTierTransition(payload);
      toast.success('Tier transition recorded');
      setTransitionForm({
        agent_id: '',
        from_stage: 'SOURCE',
        to_stage: 'TRICKLING',
        interval_ms: '',
        signature: '',
      });
      await loadTransitions();
    } catch (e: any) { toast.error(e.message); }
  };

  // --- Helpers ---

  // Render a small pill-shaped badge for inline display of enum / numeric values.
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

  // Pick a regime color, falling back to the primary theme color.
  const regimeColor = (s: string) => REGIME_COLORS[s] ?? themeColors.primary;
  // Pick a stage color, falling back to the primary theme color.
  const stageColor = (s: string) => STAGE_COLORS[s] ?? themeColors.primary;

  // Initial loading state: show a spinner panel.
  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🌊 Cognitive Cascade</h2>
          <p className="panel-subtitle">
            Record cascade readings, log flow events, and plan flow strategies across the cognitive cascade engine
          </p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading cognitive cascade...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="panel-container"
      style={{
        '--accent-primary': themeColors.primary,
        '--accent-secondary': themeColors.secondary,
      } as React.CSSProperties}
    >
      <div className="panel-header">
        <h2>🌊 Cognitive Cascade</h2>
        <p className="panel-subtitle">
          Record cascade readings, log flow events, and plan flow strategies across the cognitive cascade engine
        </p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar: high-level counts shown across all sections. */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span>
              <span className="stat-label">Agents</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span>
              <span className="stat-label">Readings</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_flows ?? '-'}</span>
              <span className="stat-label">Flows</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span>
              <span className="stat-label">Snapshots</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_plans ?? '-'}</span>
              <span className="stat-label">Plans</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_transitions ?? '-'}</span>
              <span className="stat-label">Transitions</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_cascade ?? '-'}</span>
              <span className="stat-label">Avg Cascade</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span>
              <span className="stat-label">Dominant Regime</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs: switch between the six sub-views. */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'flows', 'snapshots', 'plans', 'transitions'] as const).map(s => (
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

      {/* Overview Section: dashboard of recent activity. */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Cascade Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Flows</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_flows ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Transitions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_transitions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Cascade</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_cascade ?? '-'}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dominant Regime</div>
                <div style={{ fontSize: 18, color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</div>
              </div>
            </div>
          </div>

          {/* Recent readings card. */}
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
                          {r.regime && renderBadge(r.regime, regimeColor(r.regime))}
                          {typeof r.cascade_score !== 'undefined' && renderBadge(`cas ${r.cascade_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent flows card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Flows</h3>
            <button onClick={() => loadFlows()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {flows.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No flows recorded. Record one in the Flows section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {flows.slice(0, 10).map((f: any, i: number) => {
                  const id = f.flow_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>flow {id}{f.source ? ` · ${f.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.axis && renderBadge(f.axis, themeColors.secondary)}
                          {f.source && renderBadge(f.source, themeColors.secondary)}
                          {typeof f.before_score !== 'undefined' && typeof f.after_score !== 'undefined' && renderBadge(`${f.before_score}->${f.after_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent transitions card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Transitions</h3>
            <button onClick={() => loadTransitions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {transitions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No transitions recorded. Record one in the Transitions section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {transitions.slice(0, 10).map((c: any, i: number) => {
                  const id = c.transition_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>transition {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.from_stage && renderBadge(c.from_stage, stageColor(c.from_stage))}
                          {c.to_stage && renderBadge(c.to_stage, stageColor(c.to_stage))}
                          {c.signature && renderBadge(c.signature, themeColors.secondary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Snapshots & Plans quick refresh row. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Snapshots &amp; Plans</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
              <button onClick={() => loadSnapshots()} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>
                Refresh Snapshots ({snapshots.length})
              </button>
              <button onClick={() => loadPlans()} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>
                Refresh Plans ({plans.length})
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Readings Section: form to record + list of recent readings. */}
      {activeSection === 'readings' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reading</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={readingForm.agent_id}
                  onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })}
                  placeholder="e.g. agent_42"
                />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select
                  className="form-select"
                  value={readingForm.axis}
                  onChange={e => setReadingForm({ ...readingForm, axis: e.target.value })}
                >
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Source</label>
                <select
                  className="form-select"
                  value={readingForm.source}
                  onChange={e => setReadingForm({ ...readingForm, source: e.target.value })}
                >
                  {SOURCES.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Cascade Score</label>
                <input
                  className="form-input"
                  value={readingForm.cascade_score}
                  onChange={e => setReadingForm({ ...readingForm, cascade_score: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.6"
                />
              </div>
              <div className="form-group">
                <label>Intensity</label>
                <input
                  className="form-input"
                  value={readingForm.intensity}
                  onChange={e => setReadingForm({ ...readingForm, intensity: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.5"
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input
                  className="form-input"
                  value={readingForm.notes}
                  onChange={e => setReadingForm({ ...readingForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordReading}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Reading
            </button>
          </div>

          {/* List of recent readings, capped at 30 entries. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Readings ({readings.length})</h3>
            <button
              onClick={() => loadReadings()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
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
                          {typeof r.cascade_score !== 'undefined' && renderBadge(`cas ${r.cascade_score}`, themeColors.primary)}
                          {r.source && renderBadge(r.source, themeColors.secondary)}
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

      {/* Flows Section: form to record + list of recent flows. */}
      {activeSection === 'flows' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Flow</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={flowForm.agent_id}
                  onChange={e => setFlowForm({ ...flowForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select
                  className="form-select"
                  value={flowForm.axis}
                  onChange={e => setFlowForm({ ...flowForm, axis: e.target.value })}
                >
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Source</label>
                <select
                  className="form-select"
                  value={flowForm.source}
                  onChange={e => setFlowForm({ ...flowForm, source: e.target.value })}
                >
                  {SOURCES.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Before Score</label>
                <input
                  className="form-input"
                  value={flowForm.before_score}
                  onChange={e => setFlowForm({ ...flowForm, before_score: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.3"
                />
              </div>
              <div className="form-group">
                <label>After Score</label>
                <input
                  className="form-input"
                  value={flowForm.after_score}
                  onChange={e => setFlowForm({ ...flowForm, after_score: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.7"
                />
              </div>
              <div className="form-group">
                <label>Flow Magnitude</label>
                <input
                  className="form-input"
                  value={flowForm.flow_magnitude}
                  onChange={e => setFlowForm({ ...flowForm, flow_magnitude: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.4"
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input
                  className="form-input"
                  value={flowForm.notes}
                  onChange={e => setFlowForm({ ...flowForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordFlow}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Flow
            </button>
          </div>

          {/* List of recent flows, capped at 30 entries. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Flows ({flows.length})</h3>
            <button
              onClick={() => loadFlows()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {flows.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No flows recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {flows.slice(0, 30).map((f: any, i: number) => {
                  const id = f.flow_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>flow {id}{f.source ? ` · ${f.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.axis && renderBadge(f.axis, themeColors.secondary)}
                          {f.source && renderBadge(f.source, themeColors.secondary)}
                          {typeof f.before_score !== 'undefined' && typeof f.after_score !== 'undefined' && renderBadge(`${f.before_score}->${f.after_score}`, themeColors.primary)}
                          {typeof f.flow_magnitude !== 'undefined' && renderBadge(`mag ${f.flow_magnitude}`, themeColors.secondary)}
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

      {/* Snapshots Section: form to take + list of recent snapshots. */}
      {activeSection === 'snapshots' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Take Snapshot</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={snapshotForm.agent_id}
                  onChange={e => setSnapshotForm({ ...snapshotForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
            </div>
            <button
              onClick={handleTakeSnapshot}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Take Snapshot
            </button>
            {/* Display the raw JSON response of the most recent snapshot for inspection. */}
            {snapshotResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>
                {JSON.stringify(snapshotResult, null, 2)}
              </pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Snapshots ({snapshots.length})</h3>
            <button
              onClick={() => loadSnapshots()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
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
                          {typeof s.cascade_score !== 'undefined' && renderBadge(`cas ${s.cascade_score}`, themeColors.primary)}
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

      {/* Plans Section: form to plan a flow + list of recent plans. */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Flow</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={planForm.agent_id}
                  onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select
                  className="form-select"
                  value={planForm.strategy}
                  onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}
                >
                  {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Cascade</label>
                <input
                  className="form-input"
                  value={planForm.target_cascade}
                  onChange={e => setPlanForm({ ...planForm, target_cascade: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.8"
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input
                  className="form-input"
                  value={planForm.rationale}
                  onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })}
                  placeholder="rationale for plan"
                />
              </div>
            </div>
            <button
              onClick={handlePlanFlow}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Plan Flow
            </button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Plans ({plans.length})</h3>
            <button
              onClick={() => loadPlans()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
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
                          {typeof p.target_cascade !== 'undefined' && renderBadge(`target ${p.target_cascade}`, themeColors.primary)}
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

      {/* Transitions Section: form to record a tier transition event + list of recent transitions. */}
      {activeSection === 'transitions' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Transition</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={transitionForm.agent_id}
                  onChange={e => setTransitionForm({ ...transitionForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>From Stage</label>
                <select
                  className="form-select"
                  value={transitionForm.from_stage}
                  onChange={e => setTransitionForm({ ...transitionForm, from_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Stage</label>
                <select
                  className="form-select"
                  value={transitionForm.to_stage}
                  onChange={e => setTransitionForm({ ...transitionForm, to_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Interval (ms)</label>
                <input
                  className="form-input"
                  value={transitionForm.interval_ms}
                  onChange={e => setTransitionForm({ ...transitionForm, interval_ms: e.target.value })}
                  type="number"
                  min="0"
                  step="1"
                  placeholder="e.g. 1000"
                />
              </div>
              <div className="form-group">
                <label>Signature</label>
                <input
                  className="form-input"
                  value={transitionForm.signature}
                  onChange={e => setTransitionForm({ ...transitionForm, signature: e.target.value })}
                  placeholder="signature identifier"
                />
              </div>
            </div>
            <button
              onClick={handleRecordTransition}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Transition
            </button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Transitions ({transitions.length})</h3>
            <button
              onClick={() => loadTransitions()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {transitions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No transitions recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {transitions.slice(0, 30).map((c: any, i: number) => {
                  const id = c.transition_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>transition {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.from_stage && renderBadge(c.from_stage, stageColor(c.from_stage))}
                          {c.to_stage && renderBadge(c.to_stage, stageColor(c.to_stage))}
                          {typeof c.interval_ms !== 'undefined' && renderBadge(`${c.interval_ms}ms`, themeColors.secondary)}
                          {c.signature && renderBadge(c.signature, themeColors.primary)}
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

// Default export for compatibility with existing panel consumers that expect
// a default export from this module (matches the pattern of other panel files).
export default CognitiveCascadePanel;
