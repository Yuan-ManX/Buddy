// CognitiveTexturePanel: a React TypeScript panel for the cognitive texture engine.
//
// This panel allows operators to:
//   - View aggregate stats about cognitive texture across the system.
//   - Record texture readings for agents (axis / texture score / texture source).
//   - Record refinements (events that refine the texture of an axis).
//   - Take snapshots of an agent's current texture state.
//   - Plan refinement strategies to deliberately shape the texture profile of an agent.
//   - Record polishes (terminal / locked-in texture events).
//
// The visual style is emerald/green to match the "texture" theme (refinement, polish).

import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: emerald / green tones for cognitive texture (refinement, polish feel).
const themeColors = {
  primary: '#059669',
  secondary: '#10b981',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

// Enum values must match the backend's TextureAxis / TextureRegime /
// TextureSource / TextureStrategy / TextureStage enums exactly
// (uppercase strings).
const AXES = ['THOUGHT', 'LANGUAGE', 'IMAGERY', 'EMOTION', 'INTUITION', 'MEMORY'];
const REGIMES = ['COARSE', 'ROUGH', 'GRAINY', 'SMOOTH', 'FINE', 'SILKEN'];
const SOURCES = ['PRACTICE', 'EXPOSURE', 'REFLECTION', 'IMITATION', 'CREATION', 'MASTERY'];
const STRATEGIES = ['POLISH', 'SMOOTH', 'COMPOSE', 'LAYER', 'DISTILL', 'TEMPER'];
const STAGES = ['RAW', 'SHAPING', 'REFINING', 'POLISHED', 'LUSTERED', 'FLAWLESS'];

// Map a regime value to a badge color so a glance tells you how refined the agent is.
const REGIME_COLORS: Record<string, string> = {
  COARSE: '#9ca3af',
  ROUGH: '#a16207',
  GRAINY: '#ca8a04',
  SMOOTH: '#16a34a',
  FINE: '#059669',
  SILKEN: '#0d9488',
};

// Map a stage value to a badge color for the polish process.
const STAGE_COLORS: Record<string, string> = {
  RAW: '#9ca3af',
  SHAPING: '#a16207',
  REFINING: '#ca8a04',
  POLISHED: '#16a34a',
  LUSTERED: '#059669',
  FLAWLESS: '#0d9488',
};

export const CognitiveTexturePanel: React.FC = () => {
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
    'overview' | 'readings' | 'refinements' | 'snapshots' | 'plans' | 'polishes'
  >('overview');

  // Per-section data lists, populated lazily.
  const [readings, setReadings] = useState<any[]>([]);
  const [refinements, setRefinements] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [polishes, setPolishes] = useState<any[]>([]);
  // Stores the most recent snapshot returned from the backend (for inline JSON display).
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form state.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'THOUGHT',
    texture_score: '',
    texture_source: 'PRACTICE',
    intensity: '',
    notes: '',
  });

  // Record refinement form state.
  const [refinementForm, setRefinementForm] = useState({
    agent_id: '',
    axis: 'LANGUAGE',
    texture_source: 'REFLECTION',
    before_score: '',
    after_score: '',
    refinement_magnitude: '',
    notes: '',
  });

  // Take snapshot form state (just an agent id).
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan refinement form state.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'POLISH',
    target_texture: '',
    rationale: '',
  });

  // Record polish form state.
  const [polishForm, setPolishForm] = useState({
    agent_id: '',
    from_stage: 'RAW',
    to_stage: 'SHAPING',
    interval_ms: '',
    signature: '',
    notes: '',
  });

  // --- Loaders ---
  // Each loader is defensive: it accepts either an array, or an object that wraps
  // the array in a property (e.g. `{ readings: [...] }`). This tolerates both
  // paginated and unpaginated backend responses.

  // Fetch the global texture stats object.
  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveTexture.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive texture stats');
    } finally {
      setLoading(false);
    }
  };

  // Fetch the list of all texture readings.
  const loadReadings = async () => {
    try {
      const result = await api.cognitiveTexture.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  // Fetch the list of all refinement events.
  const loadRefinements = async () => {
    try {
      const result = await api.cognitiveTexture.listRefinements();
      const list = Array.isArray(result) ? result : (result?.refinements ?? []);
      setRefinements(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load refinements');
    }
  };

  // Fetch the list of all snapshots.
  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveTexture.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  // Fetch the list of all refinement plans.
  const loadPlans = async () => {
    try {
      const result = await api.cognitiveTexture.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Fetch the list of all polish events.
  const loadPolishes = async () => {
    try {
      const result = await api.cognitiveTexture.listPolishes();
      const list = Array.isArray(result) ? result : (result?.polishes ?? []);
      setPolishes(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load polishes');
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
      loadRefinements();
      loadSnapshots();
      loadPlans();
      loadPolishes();
    }
  }, [activeSection]);

  // --- Handlers ---

  // Submit a new texture reading.
  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    // Build the payload, applying sensible defaults for empty numeric inputs.
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      texture_score: readingForm.texture_score.trim() === '' ? 0.5 : Number(readingForm.texture_score),
      texture_source: readingForm.texture_source,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveTexture.recordReading(payload);
      toast.success('Reading recorded');
      // Reset the form to a clean default state.
      setReadingForm({
        agent_id: '',
        axis: 'THOUGHT',
        texture_score: '',
        texture_source: 'PRACTICE',
        intensity: '',
        notes: '',
      });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  // Submit a new refinement event.
  const handleRecordRefinement = async () => {
    if (!refinementForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: refinementForm.agent_id.trim(),
      axis: refinementForm.axis,
      texture_source: refinementForm.texture_source,
      before_score: refinementForm.before_score.trim() === '' ? 0.5 : Number(refinementForm.before_score),
      after_score: refinementForm.after_score.trim() === '' ? 0.5 : Number(refinementForm.after_score),
      refinement_magnitude: refinementForm.refinement_magnitude.trim() === '' ? 0 : Number(refinementForm.refinement_magnitude),
    };
    if (refinementForm.notes) payload.notes = refinementForm.notes.trim();
    try {
      await api.cognitiveTexture.recordRefinement(payload);
      toast.success('Refinement recorded');
      setRefinementForm({
        agent_id: '',
        axis: 'LANGUAGE',
        texture_source: 'REFLECTION',
        before_score: '',
        after_score: '',
        refinement_magnitude: '',
        notes: '',
      });
      await loadRefinements();
    } catch (e: any) { toast.error(e.message); }
  };

  // Take a new texture snapshot for the given agent.
  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveTexture.takeSnapshot(payload);
      // Surface the raw response inline so the operator can see what was captured.
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  // Create a new refinement plan for an agent.
  const handlePlanRefinement = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_texture: planForm.target_texture.trim() === '' ? 0 : Number(planForm.target_texture),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveTexture.planRefinement(payload);
      toast.success('Refinement plan created');
      setPlanForm({
        agent_id: '',
        strategy: 'POLISH',
        target_texture: '',
        rationale: '',
      });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  // Record a polish (final texture lock-in) event.
  const handleRecordPolish = async () => {
    if (!polishForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: polishForm.agent_id.trim(),
      from_stage: polishForm.from_stage,
      to_stage: polishForm.to_stage,
      interval_ms: polishForm.interval_ms.trim() === '' ? 0 : Number(polishForm.interval_ms),
      signature: polishForm.signature.trim(),
    };
    if (polishForm.notes) payload.notes = polishForm.notes.trim();
    try {
      await api.cognitiveTexture.recordPolish(payload);
      toast.success('Polish recorded');
      setPolishForm({
        agent_id: '',
        from_stage: 'RAW',
        to_stage: 'SHAPING',
        interval_ms: '',
        signature: '',
        notes: '',
      });
      await loadPolishes();
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
          <h2>💎 Cognitive Texture</h2>
          <p className="panel-subtitle">
            Record texture readings, log refinements, and plan polish strategies across the cognitive texture engine
          </p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading cognitive texture...</span>
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
        <h2>💎 Cognitive Texture</h2>
        <p className="panel-subtitle">
          Record texture readings, log refinements, and plan polish strategies across the cognitive texture engine
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_refinements ?? '-'}</span>
              <span className="stat-label">Refinements</span>
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_polishes ?? '-'}</span>
              <span className="stat-label">Polishes</span>
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
        {(['overview', 'readings', 'refinements', 'snapshots', 'plans', 'polishes'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Texture Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Refinements</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_refinements ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Polishes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_polishes ?? 0}</div>
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
                          {typeof r.texture_score !== 'undefined' && renderBadge(`texture ${r.texture_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent refinements card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Refinements</h3>
            <button onClick={() => loadRefinements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {refinements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No refinements recorded. Record one in the Refinements section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {refinements.slice(0, 10).map((r: any, i: number) => {
                  const id = r.refinement_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>refinement {id}{r.texture_source ? ` · ${r.texture_source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.texture_source && renderBadge(r.texture_source, themeColors.secondary)}
                          {typeof r.before_score !== 'undefined' && typeof r.after_score !== 'undefined' && renderBadge(`${r.before_score}->${r.after_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent polishes card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Polishes</h3>
            <button onClick={() => loadPolishes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {polishes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No polishes recorded. Record one in the Polishes section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {polishes.slice(0, 10).map((p: any, i: number) => {
                  const id = p.polish_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>polish {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.from_stage && renderBadge(p.from_stage, stageColor(p.from_stage))}
                          {p.to_stage && renderBadge(p.to_stage, stageColor(p.to_stage))}
                          {p.signature && renderBadge(p.signature, themeColors.secondary)}
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
                <label>Texture Source</label>
                <select
                  className="form-select"
                  value={readingForm.texture_source}
                  onChange={e => setReadingForm({ ...readingForm, texture_source: e.target.value })}
                >
                  {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Texture Score</label>
                <input
                  className="form-input"
                  value={readingForm.texture_score}
                  onChange={e => setReadingForm({ ...readingForm, texture_score: e.target.value })}
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
                          {typeof r.texture_score !== 'undefined' && renderBadge(`texture ${r.texture_score}`, themeColors.primary)}
                          {r.texture_source && renderBadge(r.texture_source, themeColors.secondary)}
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

      {/* Refinements Section: form to record + list of recent refinements. */}
      {activeSection === 'refinements' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Refinement</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={refinementForm.agent_id}
                  onChange={e => setRefinementForm({ ...refinementForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select
                  className="form-select"
                  value={refinementForm.axis}
                  onChange={e => setRefinementForm({ ...refinementForm, axis: e.target.value })}
                >
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Texture Source</label>
                <select
                  className="form-select"
                  value={refinementForm.texture_source}
                  onChange={e => setRefinementForm({ ...refinementForm, texture_source: e.target.value })}
                >
                  {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Before Score</label>
                <input
                  className="form-input"
                  value={refinementForm.before_score}
                  onChange={e => setRefinementForm({ ...refinementForm, before_score: e.target.value })}
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
                  value={refinementForm.after_score}
                  onChange={e => setRefinementForm({ ...refinementForm, after_score: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.7"
                />
              </div>
              <div className="form-group">
                <label>Refinement Magnitude</label>
                <input
                  className="form-input"
                  value={refinementForm.refinement_magnitude}
                  onChange={e => setRefinementForm({ ...refinementForm, refinement_magnitude: e.target.value })}
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
                  value={refinementForm.notes}
                  onChange={e => setRefinementForm({ ...refinementForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordRefinement}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Refinement
            </button>
          </div>

          {/* List of recent refinements, capped at 30 entries. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Refinements ({refinements.length})</h3>
            <button
              onClick={() => loadRefinements()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {refinements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No refinements recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {refinements.slice(0, 30).map((r: any, i: number) => {
                  const id = r.refinement_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>refinement {id}{r.texture_source ? ` · ${r.texture_source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.texture_source && renderBadge(r.texture_source, themeColors.secondary)}
                          {typeof r.before_score !== 'undefined' && typeof r.after_score !== 'undefined' && renderBadge(`${r.before_score}->${r.after_score}`, themeColors.primary)}
                          {typeof r.refinement_magnitude !== 'undefined' && renderBadge(`mag ${r.refinement_magnitude}`, themeColors.secondary)}
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
                          {typeof s.texture_score !== 'undefined' && renderBadge(`texture ${s.texture_score}`, themeColors.primary)}
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

      {/* Plans Section: form to plan a refinement + list of recent plans. */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Refinement</h3>
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
                <label>Target Texture</label>
                <input
                  className="form-input"
                  value={planForm.target_texture}
                  onChange={e => setPlanForm({ ...planForm, target_texture: e.target.value })}
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
              onClick={handlePlanRefinement}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Plan Refinement
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
                          {typeof p.target_texture !== 'undefined' && renderBadge(`target ${p.target_texture}`, themeColors.primary)}
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

      {/* Polishes Section: form to record a polish event + list of recent polishes. */}
      {activeSection === 'polishes' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Polish</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={polishForm.agent_id}
                  onChange={e => setPolishForm({ ...polishForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>From Stage</label>
                <select
                  className="form-select"
                  value={polishForm.from_stage}
                  onChange={e => setPolishForm({ ...polishForm, from_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Stage</label>
                <select
                  className="form-select"
                  value={polishForm.to_stage}
                  onChange={e => setPolishForm({ ...polishForm, to_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Interval (ms)</label>
                <input
                  className="form-input"
                  value={polishForm.interval_ms}
                  onChange={e => setPolishForm({ ...polishForm, interval_ms: e.target.value })}
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
                  value={polishForm.signature}
                  onChange={e => setPolishForm({ ...polishForm, signature: e.target.value })}
                  placeholder="signature identifier"
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input
                  className="form-input"
                  value={polishForm.notes}
                  onChange={e => setPolishForm({ ...polishForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordPolish}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Polish
            </button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Polishes ({polishes.length})</h3>
            <button
              onClick={() => loadPolishes()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {polishes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No polishes recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {polishes.slice(0, 30).map((p: any, i: number) => {
                  const id = p.polish_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>polish {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.from_stage && renderBadge(p.from_stage, stageColor(p.from_stage))}
                          {p.to_stage && renderBadge(p.to_stage, stageColor(p.to_stage))}
                          {typeof p.interval_ms !== 'undefined' && renderBadge(`${p.interval_ms}ms`, themeColors.secondary)}
                          {p.signature && renderBadge(p.signature, themeColors.primary)}
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
export default CognitiveTexturePanel;