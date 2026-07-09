// CognitivePanel: a shared, config-driven React TypeScript panel for any
// standard-pattern cognitive engine.
//
// This component renders the full cognitive engine UI (stats, readings,
// secondary records, snapshots, plans, shifts) driven by a CognitiveEngineConfig
// looked up from the COGNITIVE_ENGINES registry via the `engineKey` prop.
//

import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import { COGNITIVE_ENGINES, type CognitiveEngineConfig } from '../config/cognitiveEngines';

// Theme colors and all engine-specific constants are resolved from the
// COGNITIVE_ENGINES config registry at render time.

// Enum values, theme colors, and per-regime/stage colors are all resolved
// from the engine config (see cognitiveEngines.ts).



interface CognitivePanelProps {
  engineKey: string;
}

export const CognitivePanel: React.FC<CognitivePanelProps> = ({ engineKey }) => {
  const config = COGNITIVE_ENGINES[engineKey];
  if (!config) {
    return <div className="panel-container"><div className="panel-header"><h2>Unknown engine: {engineKey}</h2></div></div>;
  }
  const themeColors = config.theme;
  const AXES = config.axes;
  const REGIMES = config.regimes;
  const SOURCES = config.sources;
  const STRATEGIES = config.strategies;
  const STAGES = config.stages;
  const REGIME_COLORS = config.regimeColors;
  const STAGE_COLORS = config.stageColors;
  // Resolve the cognitive API namespace for this engine.
  const cognitiveApi: any = (api as any)[config.apiKey];

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
    'overview' | 'readings' | 'secondary' | 'snapshots' | 'plans' | 'shifts'
  >('overview');

  // Per-section data lists, populated lazily.
  const [readings, setReadings] = useState<any[]>([]);
  const [secondaryRecords, setSecondaryRecords] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [shifts, setShifts] = useState<any[]>([]);
  // Stores the most recent snapshot returned from the backend (for inline JSON display).
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form state.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: config.defaults.axis,
    [config.scoreField]: '',
    source: config.defaults.source,
    intensity: '',
    notes: '',
  });

  // Record lichen form state.
  const [secondaryForm, setSecondaryForm] = useState({
    agent_id: '',
    axis: config.defaults.axis,
    source: config.defaults.source,
    before_score: '',
    after_score: '',
    [config.magnitudeField]: '',
    notes: '',
  });

  // Take snapshot form state (just an agent id).
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan lichen form state.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: config.defaults.strategy,
    [config.targetField]: '',
    rationale: '',
  });

  // Record shift form state (no notes field on this record type).
  const [shiftForm, setShiftForm] = useState({
    agent_id: '',
    from_stage: config.defaults.fromStage,
    to_stage: config.defaults.toStage,
    interval_ms: '',
    signature: '',
  });

  // --- Loaders ---
  // Each loader is defensive: it accepts either an array, or an object that wraps
  // the array in a property (e.g. `{ readings: [...] }`). This tolerates both
  // paginated and unpaginated backend responses.

  // Fetch the global tundra stats object.
  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await cognitiveApi.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive tundra stats');
    } finally {
      setLoading(false);
    }
  };

  // Fetch the list of all tundra readings.
  const loadReadings = async () => {
    try {
      const result = await cognitiveApi.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? result?.items ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  // Fetch the list of all lichen events.
  const loadSecondary = async () => {
    try {
      const result = await cognitiveApi[`list${config.secPlural}`]();
      const list = Array.isArray(result) ? result : (result?.[config.secSlug] ?? result?.items ?? []);
      setSecondaryRecords(list);
    } catch (e: any) {
      toast.error(e.message || `Failed to load ${config.secSlug}`);
    }
  };

  // Fetch the list of all snapshots.
  const loadSnapshots = async () => {
    try {
      const result = await cognitiveApi.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? result?.items ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  // Fetch the list of all lichen plans.
  const loadPlans = async () => {
    try {
      const result = await cognitiveApi.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? result?.items ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Fetch the list of all shift events.
  const loadShifts = async () => {
    try {
      const result = await cognitiveApi[`list${config.tertClass}Shifts`]();
      const list = Array.isArray(result) ? result : (result?.shifts ?? result?.items ?? []);
      setShifts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load shifts');
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
      loadSecondary();
      loadSnapshots();
      loadPlans();
      loadShifts();
    }
  }, [activeSection]);

  // --- Handlers ---

  // Submit a new tundra reading.
  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    // Build the payload, applying sensible defaults for empty numeric inputs.
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      [config.scoreField]: readingForm[config.scoreField].trim() === '' ? 0.5 : Number(readingForm.tundra_score),
      source: readingForm.source,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await cognitiveApi.recordReading(payload);
      toast.success('Reading recorded');
      // Reset the form to a clean default state.
      setReadingForm({
        agent_id: '',
        axis: config.defaults.axis,
        [config.scoreField]: '',
        source: config.defaults.source,
        intensity: '',
        notes: '',
      });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  // Submit a new lichen event.
  const handleRecordSecondary = async () => {
    if (!secondaryForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: secondaryForm.agent_id.trim(),
      axis: secondaryForm.axis,
      source: secondaryForm.source,
      before_score: secondaryForm.before_score.trim() === '' ? 0.5 : Number(secondaryForm.before_score),
      after_score: secondaryForm.after_score.trim() === '' ? 0.5 : Number(secondaryForm.after_score),
      [config.magnitudeField]: secondaryForm[config.magnitudeField].trim() === '' ? 0 : Number(secondaryForm.lichen_magnitude),
    };
    if (secondaryForm.notes) payload.notes = secondaryForm.notes.trim();
    try {
      await cognitiveApi[`record${config.secSingular}`](payload);
      toast.success('Lichen recorded');
      setSecondaryForm({
        agent_id: '',
        axis: config.defaults.axis,
        source: config.defaults.source,
        before_score: '',
        after_score: '',
        [config.magnitudeField]: '',
        notes: '',
      });
      await loadSecondary();
    } catch (e: any) { toast.error(e.message); }
  };

  // Take a new tundra snapshot for the given agent.
  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await cognitiveApi.takeSnapshot(payload);
      // Surface the raw response inline so the operator can see what was captured.
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  // Create a new lichen plan for an agent.
  const handlePlanSecondary = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      [config.targetField]: planForm[config.targetField].trim() === '' ? 0 : Number(planForm.target_tundra),
      rationale: planForm.rationale.trim(),
    };
    try {
      await cognitiveApi[`plan${config.secSingular}`](payload);
      toast.success('Lichen plan created');
      setPlanForm({
        agent_id: '',
        strategy: config.defaults.strategy,
        [config.targetField]: '',
        rationale: '',
      });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  // Record a shift (final tundra stage transition) event.
  // Note: shift records do not accept a notes field on the backend.
  const handleRecordShift = async () => {
    if (!shiftForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: shiftForm.agent_id.trim(),
      from_stage: shiftForm.from_stage,
      to_stage: shiftForm.to_stage,
      interval_ms: shiftForm.interval_ms.trim() === '' ? 0 : Number(shiftForm.interval_ms),
      signature: shiftForm.signature.trim(),
    };
    try {
      await cognitiveApi[`record${config.tertClass}Shift`](payload);
      toast.success('Shift recorded');
      setShiftForm({
        agent_id: '',
        from_stage: config.defaults.fromStage,
        to_stage: config.defaults.toStage,
        interval_ms: '',
        signature: '',
      });
      await loadShifts();
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
          <h2>{config.emoji} {config.title}</h2>
          <p className="panel-subtitle">
            {`Record ${config.engineName} readings, log ${config.secSlugSingular} events, and plan ${config.secSlugSingular} across the ${config.title} engine`}
          </p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading cognitive engine...</span>
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
        <h2>{config.emoji} {config.title}</h2>
        <p className="panel-subtitle">
          {`Record ${config.engineName} readings, log ${config.secSlugSingular} events, and plan ${config.secSlugSingular} across the ${config.title} engine`}
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats[`total_${config.secSlug}`] ?? '-'}</span>
              <span className="stat-label">Lichens</span>
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_shifts ?? '-'}</span>
              <span className="stat-label">Shifts</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats[`avg_${config.engineName}`] ?? '-'}</span>
              <span className="stat-label">Avg {config.scoreLabel}</span>
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
        {(['overview', 'readings', 'secondary', 'snapshots', 'plans', 'shifts'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s === 'secondary' ? config.secPlural : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Section: dashboard of recent activity. */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>{config.scoreLabel} Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total {config.secPlural}</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats[`total_${config.secSlug}`] ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Shifts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_shifts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg {config.scoreLabel}</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats[`avg_${config.engineName}`] ?? '-'}</div>
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
                          {typeof r[config.scoreField] !== 'undefined' && renderBadge(`${config.engineName} ${r[config.scoreField]}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent lichens card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent {config.secPlural}</h3>
            <button onClick={() => loadSecondary()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {secondaryRecords.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No {config.secSlug} recorded. Record one in the {config.secPlural} section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {secondaryRecords.slice(0, 10).map((a: any, i: number) => {
                  const id = a[`${config.secSlugSingular}_id`] ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{config.secSlugSingular} {id}{a.source ? ` · ${a.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.axis && renderBadge(a.axis, themeColors.secondary)}
                          {a.source && renderBadge(a.source, themeColors.secondary)}
                          {typeof a.before_score !== 'undefined' && typeof a.after_score !== 'undefined' && renderBadge(`${a.before_score}->${a.after_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent shifts card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Shifts</h3>
            <button onClick={() => loadShifts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {shifts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No shifts recorded. Record one in the Shifts section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {shifts.slice(0, 10).map((c: any, i: number) => {
                  const id = c.shift_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>shift {id}</div>
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
                <label>{config.scoreLabel} Score</label>
                <input
                  className="form-input"
                  value={readingForm[config.scoreField]}
                  onChange={e => setReadingForm({ ...readingForm, [config.scoreField]: e.target.value })}
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
                          {typeof r[config.scoreField] !== 'undefined' && renderBadge(`${config.engineName} ${r[config.scoreField]}`, themeColors.primary)}
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

      {/* Lichens Section: form to record + list of recent lichens. */}
      {activeSection === 'secondary' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record {config.secSingular}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={secondaryForm.agent_id}
                  onChange={e => setSecondaryForm({ ...secondaryForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select
                  className="form-select"
                  value={secondaryForm.axis}
                  onChange={e => setSecondaryForm({ ...secondaryForm, axis: e.target.value })}
                >
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Source</label>
                <select
                  className="form-select"
                  value={secondaryForm.source}
                  onChange={e => setSecondaryForm({ ...secondaryForm, source: e.target.value })}
                >
                  {SOURCES.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Before Score</label>
                <input
                  className="form-input"
                  value={secondaryForm.before_score}
                  onChange={e => setSecondaryForm({ ...secondaryForm, before_score: e.target.value })}
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
                  value={secondaryForm.after_score}
                  onChange={e => setSecondaryForm({ ...secondaryForm, after_score: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.7"
                />
              </div>
              <div className="form-group">
                <label>{config.secSingular} Magnitude</label>
                <input
                  className="form-input"
                  value={secondaryForm[config.magnitudeField]}
                  onChange={e => setSecondaryForm({ ...secondaryForm, [config.magnitudeField]: e.target.value })}
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
                  value={secondaryForm.notes}
                  onChange={e => setSecondaryForm({ ...secondaryForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordSecondary}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record {config.secSingular}
            </button>
          </div>

          {/* List of recent lichens, capped at 30 entries. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>{config.secPlural} ({secondaryRecords.length})</h3>
            <button
              onClick={() => loadSecondary()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {secondaryRecords.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No {config.secSlug} recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {secondaryRecords.slice(0, 30).map((a: any, i: number) => {
                  const id = a[`${config.secSlugSingular}_id`] ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{config.secSlugSingular} {id}{a.source ? ` · ${a.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.axis && renderBadge(a.axis, themeColors.secondary)}
                          {a.source && renderBadge(a.source, themeColors.secondary)}
                          {typeof a.before_score !== 'undefined' && typeof a.after_score !== 'undefined' && renderBadge(`${a.before_score}->${a.after_score}`, themeColors.primary)}
                          {typeof a[config.magnitudeField] !== 'undefined' && renderBadge(`mag ${a[config.magnitudeField]}`, themeColors.secondary)}
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
                          {typeof s[config.scoreField] !== 'undefined' && renderBadge(`${config.engineName} ${s[config.scoreField]}`, themeColors.primary)}
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

      {/* Plans Section: form to plan a lichen + list of recent plans. */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan {config.secSingular}</h3>
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
                <label>Target {config.scoreLabel}</label>
                <input
                  className="form-input"
                  value={planForm[config.targetField]}
                  onChange={e => setPlanForm({ ...planForm, [config.targetField]: e.target.value })}
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
              onClick={handlePlanSecondary}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Plan {config.secSingular}
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
                          {typeof p[config.targetField] !== 'undefined' && renderBadge(`target ${p[config.targetField]}`, themeColors.primary)}
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

      {/* Shifts Section: form to record a shift event + list of recent shifts. */}
      {activeSection === 'shifts' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Shift</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={shiftForm.agent_id}
                  onChange={e => setShiftForm({ ...shiftForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>From Stage</label>
                <select
                  className="form-select"
                  value={shiftForm.from_stage}
                  onChange={e => setShiftForm({ ...shiftForm, from_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Stage</label>
                <select
                  className="form-select"
                  value={shiftForm.to_stage}
                  onChange={e => setShiftForm({ ...shiftForm, to_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Interval (ms)</label>
                <input
                  className="form-input"
                  value={shiftForm.interval_ms}
                  onChange={e => setShiftForm({ ...shiftForm, interval_ms: e.target.value })}
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
                  value={shiftForm.signature}
                  onChange={e => setShiftForm({ ...shiftForm, signature: e.target.value })}
                  placeholder="signature identifier"
                />
              </div>
            </div>
            <button
              onClick={handleRecordShift}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Shift
            </button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Shifts ({shifts.length})</h3>
            <button
              onClick={() => loadShifts()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {shifts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No shifts recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {shifts.slice(0, 30).map((c: any, i: number) => {
                  const id = c.shift_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>shift {id}</div>
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

// Note: this component is used via named export <CognitivePanel engineKey="..." />.
