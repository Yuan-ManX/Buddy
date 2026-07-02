// CognitiveTidePanel: a React TypeScript panel for the cognitive tide engine.
//
// This panel allows operators to:
//   - View aggregate stats about cognitive tide across the system.
//   - Record tide readings for agents (axis / tide score / source).
//   - Record surges (events that shift the tide of an axis).
//   - Take snapshots of an agent's current tide state.
//   - Plan surge strategies to deliberately shape the tide profile of an agent.
//   - Record phase shifts (terminal / locked-in tide stage transitions).
//
// The visual style is cyan to match the "tide" theme (flow / wave / current forces).

import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: cyan tones for cognitive tide (flow / wave / current feel).
const themeColors = {
  primary: '#0891b2',
  secondary: '#06b6d4',
  bg: '#ecfeff',
  border: '#a5f3fc',
  accent: '#cffafe',
  text: '#164e63',
};

// Enum values must match the backend's TideAxis / TideRegime /
// TideSource / TideStrategy / TideStage enums exactly
// (uppercase strings).
const AXES = ['FLOW', 'WAVE', 'CURRENT', 'SURGE', 'EBB', 'CREST'];
const REGIMES = ['STAGNANT', 'LOW', 'RISING', 'HIGH', 'CRESTING', 'TIDAL'];
const SOURCES = ['GRAVITY', 'WIND', 'PRESSURE', 'LUNAR', 'THERMAL', 'CORIOLIS'];
const STRATEGIES = ['CHANNEL', 'HARNESS', 'RELEASE', 'DAM', 'ACCELERATE', 'CALM'];
const STAGES = ['EBB', 'FLOOD', 'RISING', 'HIGH', 'CRESTING', 'RECEDING'];

// Map a regime value to a badge color so a glance tells you how strong the tide is.
const REGIME_COLORS: Record<string, string> = {
  STAGNANT: '#1f2937',
  LOW: '#6b7280',
  RISING: '#06b6d4',
  HIGH: '#0891b2',
  CRESTING: '#0e7490',
  TIDAL: '#164e63',
};

// Map a stage value to a badge color for the phase shift process.
const STAGE_COLORS: Record<string, string> = {
  EBB: '#1f2937',
  FLOOD: '#6b7280',
  RISING: '#06b6d4',
  HIGH: '#0891b2',
  CRESTING: '#0e7490',
  RECEDING: '#164e63',
};

export const CognitiveTidePanel: React.FC = () => {
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
    'overview' | 'readings' | 'surges' | 'snapshots' | 'plans' | 'phases'
  >('overview');

  // Per-section data lists, populated lazily.
  const [readings, setReadings] = useState<any[]>([]);
  const [surges, setSurges] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [phases, setPhases] = useState<any[]>([]);
  // Stores the most recent snapshot returned from the backend (for inline JSON display).
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form state.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'FLOW',
    tide_score: '',
    source: 'GRAVITY',
    intensity: '',
    notes: '',
  });

  // Record surge form state.
  const [surgeForm, setSurgeForm] = useState({
    agent_id: '',
    axis: 'FLOW',
    source: 'GRAVITY',
    before_score: '',
    after_score: '',
    surge_magnitude: '',
    notes: '',
  });

  // Take snapshot form state (just an agent id).
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan surge form state.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'CHANNEL',
    target_tide: '',
    rationale: '',
  });

  // Record phase shift form state (no notes field on this record type).
  const [phaseForm, setPhaseForm] = useState({
    agent_id: '',
    from_stage: 'EBB',
    to_stage: 'FLOOD',
    interval_ms: '',
    signature: '',
  });

  // --- Loaders ---
  // Each loader is defensive: it accepts either an array, or an object that wraps
  // the array in a property (e.g. `{ readings: [...] }`). This tolerates both
  // paginated and unpaginated backend responses.

  // Fetch the global tide stats object.
  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveTide.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive tide stats');
    } finally {
      setLoading(false);
    }
  };

  // Fetch the list of all tide readings.
  const loadReadings = async () => {
    try {
      const result = await api.cognitiveTide.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? result?.items ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  // Fetch the list of all surge events.
  const loadSurges = async () => {
    try {
      const result = await api.cognitiveTide.listSurges();
      const list = Array.isArray(result) ? result : (result?.surges ?? result?.items ?? []);
      setSurges(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load surges');
    }
  };

  // Fetch the list of all snapshots.
  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveTide.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? result?.items ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  // Fetch the list of all surge plans.
  const loadPlans = async () => {
    try {
      const result = await api.cognitiveTide.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? result?.items ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Fetch the list of all phase shift events.
  const loadPhases = async () => {
    try {
      const result = await api.cognitiveTide.listPhaseShifts();
      const list = Array.isArray(result) ? result : (result?.phases ?? result?.items ?? []);
      setPhases(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load phases');
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
      loadSurges();
      loadSnapshots();
      loadPlans();
      loadPhases();
    }
  }, [activeSection]);

  // --- Handlers ---

  // Submit a new tide reading.
  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    // Build the payload, applying sensible defaults for empty numeric inputs.
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      tide_score: readingForm.tide_score.trim() === '' ? 0.5 : Number(readingForm.tide_score),
      source: readingForm.source,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveTide.recordReading(payload);
      toast.success('Reading recorded');
      // Reset the form to a clean default state.
      setReadingForm({
        agent_id: '',
        axis: 'FLOW',
        tide_score: '',
        source: 'GRAVITY',
        intensity: '',
        notes: '',
      });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  // Submit a new surge event.
  const handleRecordSurge = async () => {
    if (!surgeForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: surgeForm.agent_id.trim(),
      axis: surgeForm.axis,
      source: surgeForm.source,
      before_score: surgeForm.before_score.trim() === '' ? 0.5 : Number(surgeForm.before_score),
      after_score: surgeForm.after_score.trim() === '' ? 0.5 : Number(surgeForm.after_score),
      surge_magnitude: surgeForm.surge_magnitude.trim() === '' ? 0 : Number(surgeForm.surge_magnitude),
    };
    if (surgeForm.notes) payload.notes = surgeForm.notes.trim();
    try {
      await api.cognitiveTide.recordSurge(payload);
      toast.success('Surge recorded');
      setSurgeForm({
        agent_id: '',
        axis: 'FLOW',
        source: 'GRAVITY',
        before_score: '',
        after_score: '',
        surge_magnitude: '',
        notes: '',
      });
      await loadSurges();
    } catch (e: any) { toast.error(e.message); }
  };

  // Take a new tide snapshot for the given agent.
  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveTide.takeSnapshot(payload);
      // Surface the raw response inline so the operator can see what was captured.
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  // Create a new surge plan for an agent.
  const handlePlanSurge = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_tide: planForm.target_tide.trim() === '' ? 0 : Number(planForm.target_tide),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveTide.planSurge(payload);
      toast.success('Surge plan created');
      setPlanForm({
        agent_id: '',
        strategy: 'CHANNEL',
        target_tide: '',
        rationale: '',
      });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  // Record a phase shift (final tide stage transition) event.
  // Note: phase shift records do not accept a notes field on the backend.
  const handleRecordPhaseShift = async () => {
    if (!phaseForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: phaseForm.agent_id.trim(),
      from_stage: phaseForm.from_stage,
      to_stage: phaseForm.to_stage,
      interval_ms: phaseForm.interval_ms.trim() === '' ? 0 : Number(phaseForm.interval_ms),
      signature: phaseForm.signature.trim(),
    };
    try {
      await api.cognitiveTide.recordPhaseShift(payload);
      toast.success('Phase shift recorded');
      setPhaseForm({
        agent_id: '',
        from_stage: 'EBB',
        to_stage: 'FLOOD',
        interval_ms: '',
        signature: '',
      });
      await loadPhases();
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
          <h2>🌊 Cognitive Tide</h2>
          <p className="panel-subtitle">
            Record tide readings, log surge events, and plan channeling across the cognitive tide engine
          </p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading cognitive tide...</span>
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
        <h2>🌊 Cognitive Tide</h2>
        <p className="panel-subtitle">
          Record tide readings, log surge events, and plan channeling across the cognitive tide engine
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_surges ?? '-'}</span>
              <span className="stat-label">Surges</span>
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_phases ?? '-'}</span>
              <span className="stat-label">Phases</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_tide ?? '-'}</span>
              <span className="stat-label">Avg Tide</span>
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
        {(['overview', 'readings', 'surges', 'snapshots', 'plans', 'phases'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Tide Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Surges</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_surges ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Phases</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_phases ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Tide</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_tide ?? '-'}</div>
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
                          {typeof r.tide_score !== 'undefined' && renderBadge(`tide ${r.tide_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent surges card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Surges</h3>
            <button onClick={() => loadSurges()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {surges.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No surges recorded. Record one in the Surges section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {surges.slice(0, 10).map((a: any, i: number) => {
                  const id = a.surge_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>surge {id}{a.source ? ` · ${a.source}` : ''}</div>
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

          {/* Recent phases card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Phases</h3>
            <button onClick={() => loadPhases()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {phases.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No phases recorded. Record one in the Phases section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {phases.slice(0, 10).map((c: any, i: number) => {
                  const id = c.phase_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>phase {id}</div>
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
                <label>Tide Score</label>
                <input
                  className="form-input"
                  value={readingForm.tide_score}
                  onChange={e => setReadingForm({ ...readingForm, tide_score: e.target.value })}
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
                          {typeof r.tide_score !== 'undefined' && renderBadge(`tide ${r.tide_score}`, themeColors.primary)}
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

      {/* Surges Section: form to record + list of recent surges. */}
      {activeSection === 'surges' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Surge</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={surgeForm.agent_id}
                  onChange={e => setSurgeForm({ ...surgeForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select
                  className="form-select"
                  value={surgeForm.axis}
                  onChange={e => setSurgeForm({ ...surgeForm, axis: e.target.value })}
                >
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Source</label>
                <select
                  className="form-select"
                  value={surgeForm.source}
                  onChange={e => setSurgeForm({ ...surgeForm, source: e.target.value })}
                >
                  {SOURCES.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Before Score</label>
                <input
                  className="form-input"
                  value={surgeForm.before_score}
                  onChange={e => setSurgeForm({ ...surgeForm, before_score: e.target.value })}
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
                  value={surgeForm.after_score}
                  onChange={e => setSurgeForm({ ...surgeForm, after_score: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.7"
                />
              </div>
              <div className="form-group">
                <label>Surge Magnitude</label>
                <input
                  className="form-input"
                  value={surgeForm.surge_magnitude}
                  onChange={e => setSurgeForm({ ...surgeForm, surge_magnitude: e.target.value })}
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
                  value={surgeForm.notes}
                  onChange={e => setSurgeForm({ ...surgeForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordSurge}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Surge
            </button>
          </div>

          {/* List of recent surges, capped at 30 entries. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Surges ({surges.length})</h3>
            <button
              onClick={() => loadSurges()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {surges.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No surges recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {surges.slice(0, 30).map((a: any, i: number) => {
                  const id = a.surge_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>surge {id}{a.source ? ` · ${a.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.axis && renderBadge(a.axis, themeColors.secondary)}
                          {a.source && renderBadge(a.source, themeColors.secondary)}
                          {typeof a.before_score !== 'undefined' && typeof a.after_score !== 'undefined' && renderBadge(`${a.before_score}->${a.after_score}`, themeColors.primary)}
                          {typeof a.surge_magnitude !== 'undefined' && renderBadge(`mag ${a.surge_magnitude}`, themeColors.secondary)}
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
                          {typeof s.tide_score !== 'undefined' && renderBadge(`tide ${s.tide_score}`, themeColors.primary)}
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

      {/* Plans Section: form to plan a surge + list of recent plans. */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Surge</h3>
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
                <label>Target Tide</label>
                <input
                  className="form-input"
                  value={planForm.target_tide}
                  onChange={e => setPlanForm({ ...planForm, target_tide: e.target.value })}
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
              onClick={handlePlanSurge}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Plan Surge
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
                          {typeof p.target_tide !== 'undefined' && renderBadge(`target ${p.target_tide}`, themeColors.primary)}
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

      {/* Phases Section: form to record a phase shift event + list of recent phases. */}
      {activeSection === 'phases' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Phase Shift</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={phaseForm.agent_id}
                  onChange={e => setPhaseForm({ ...phaseForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>From Stage</label>
                <select
                  className="form-select"
                  value={phaseForm.from_stage}
                  onChange={e => setPhaseForm({ ...phaseForm, from_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Stage</label>
                <select
                  className="form-select"
                  value={phaseForm.to_stage}
                  onChange={e => setPhaseForm({ ...phaseForm, to_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Interval (ms)</label>
                <input
                  className="form-input"
                  value={phaseForm.interval_ms}
                  onChange={e => setPhaseForm({ ...phaseForm, interval_ms: e.target.value })}
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
                  value={phaseForm.signature}
                  onChange={e => setPhaseForm({ ...phaseForm, signature: e.target.value })}
                  placeholder="signature identifier"
                />
              </div>
            </div>
            <button
              onClick={handleRecordPhaseShift}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Phase Shift
            </button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Phases ({phases.length})</h3>
            <button
              onClick={() => loadPhases()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {phases.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No phases recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {phases.slice(0, 30).map((c: any, i: number) => {
                  const id = c.phase_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>phase {id}</div>
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
export default CognitiveTidePanel;
