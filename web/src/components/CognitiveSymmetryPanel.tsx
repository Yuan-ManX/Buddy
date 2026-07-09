// CognitiveSymmetryPanel: a React TypeScript panel for the cognitive symmetry engine.
//
// This panel allows operators to:
//   - View aggregate stats about cognitive symmetry across the system.
//   - Record symmetry readings for agents (axis / symmetry score / asymmetry source).
//   - Record reflections (events that mirror / correct an asymmetry).
//   - Take snapshots of an agent's current symmetry state.
//   - Plan correction strategies to deliberately shape the symmetry profile of an agent.
//   - Record alignments (terminal / locked-in symmetry events).
//
// The visual style is rose/pink to match the "symmetry" theme (mirror, reflection).

import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: rose / pink tones for cognitive symmetry (mirror, reflection feel).
const themeColors = {
  primary: '#be185d',
  secondary: '#ec4899',
  bg: '#fdf2f8',
  border: '#fbcfe8',
  accent: '#fce7f3',
  text: '#831843',
};

// Enum values must match the backend's SymmetryAxis / SymmetryRegime /
// SymmetryAsymmetrySource / SymmetryStrategy / SymmetryStage enums exactly
// (uppercase strings).
const AXES = ['REASONING', 'EMOTION', 'PERCEPTION', 'ACTION', 'MEMORY', 'IDENTITY'];
const REGIMES = ['ASYMMETRIC', 'SKEWED', 'IRREGULAR', 'PARTIAL', 'SYMMETRIC', 'HARMONIC'];
const SOURCES = ['BIAS', 'TRAUMA', 'HABIT', 'PREFERENCE', 'CULTURE', 'SALIENCE'];
const STRATEGIES = ['MIRROR', 'ROTATE', 'REFLECT', 'BALANCE', 'CALIBRATE', 'DISSOLVE'];
const STAGES = ['BROKEN', 'TILTING', 'ALIGNING', 'MIRRORING', 'BALANCED', 'HARMONIZED'];

// Map a regime value to a badge color so a glance tells you how symmetric the agent is.
const REGIME_COLORS: Record<string, string> = {
  ASYMMETRIC: '#dc2626',
  SKEWED: '#ea580c',
  IRREGULAR: '#ca8a04',
  PARTIAL: '#0ea5e9',
  SYMMETRIC: '#be185d',
  HARMONIC: '#16a34a',
};

// Map a stage value to a badge color for the alignment process.
const STAGE_COLORS: Record<string, string> = {
  BROKEN: '#dc2626',
  TILTING: '#ea580c',
  ALIGNING: '#ca8a04',
  MIRRORING: '#ec4899',
  BALANCED: '#be185d',
  HARMONIZED: '#16a34a',
};

export const CognitiveSymmetryPanel: React.FC = () => {
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
    'overview' | 'readings' | 'reflections' | 'snapshots' | 'plans' | 'alignments'
  >('overview');

  // Per-section data lists, populated lazily.
  const [readings, setReadings] = useState<any[]>([]);
  const [reflections, setReflections] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [alignments, setAlignments] = useState<any[]>([]);
  // Stores the most recent snapshot returned from the backend (for inline JSON display).
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form state.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'REASONING',
    symmetry_score: '',
    asymmetry_source: 'BIAS',
    intensity: '',
    notes: '',
  });

  // Record reflection form state.
  const [reflectionForm, setReflectionForm] = useState({
    agent_id: '',
    axis: 'EMOTION',
    asymmetry_source: 'HABIT',
    before_score: '',
    after_score: '',
    reflection_magnitude: '',
    notes: '',
  });

  // Take snapshot form state (just an agent id).
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan correction form state.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'BALANCE',
    target_symmetry: '',
    rationale: '',
  });

  // Record alignment form state.
  const [alignmentForm, setAlignmentForm] = useState({
    agent_id: '',
    from_stage: 'BROKEN',
    to_stage: 'TILTING',
    interval_ms: '',
    signature: '',
    notes: '',
  });

  // --- Loaders ---
  // Each loader is defensive: it accepts either an array, or an object that wraps
  // the array in a property (e.g. `{ readings: [...] }`). This tolerates both
  // paginated and unpaginated backend responses.

  // Fetch the global symmetry stats object.
  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveSymmetry.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive symmetry stats');
    } finally {
      setLoading(false);
    }
  };

  // Fetch the list of all symmetry readings.
  const loadReadings = async () => {
    try {
      const result = await api.cognitiveSymmetry.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  // Fetch the list of all reflection events.
  const loadReflections = async () => {
    try {
      const result = await api.cognitiveSymmetry.listReflections();
      const list = Array.isArray(result) ? result : (result?.reflections ?? []);
      setReflections(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load reflections');
    }
  };

  // Fetch the list of all snapshots.
  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveSymmetry.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  // Fetch the list of all correction plans.
  const loadPlans = async () => {
    try {
      const result = await api.cognitiveSymmetry.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Fetch the list of all alignment events.
  const loadAlignments = async () => {
    try {
      const result = await api.cognitiveSymmetry.listAlignments();
      const list = Array.isArray(result) ? result : (result?.alignments ?? []);
      setAlignments(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load alignments');
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
      loadReflections();
      loadSnapshots();
      loadPlans();
      loadAlignments();
    }
  }, [activeSection]);

  // --- Handlers ---

  // Submit a new symmetry reading.
  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    // Build the payload, applying sensible defaults for empty numeric inputs.
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      symmetry_score: readingForm.symmetry_score.trim() === '' ? 0.5 : Number(readingForm.symmetry_score),
      asymmetry_source: readingForm.asymmetry_source,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveSymmetry.recordReading(payload);
      toast.success('Reading recorded');
      // Reset the form to a clean default state.
      setReadingForm({
        agent_id: '',
        axis: 'REASONING',
        symmetry_score: '',
        asymmetry_source: 'BIAS',
        intensity: '',
        notes: '',
      });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  // Submit a new reflection event.
  const handleRecordReflection = async () => {
    if (!reflectionForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: reflectionForm.agent_id.trim(),
      axis: reflectionForm.axis,
      asymmetry_source: reflectionForm.asymmetry_source,
      before_score: reflectionForm.before_score.trim() === '' ? 0.5 : Number(reflectionForm.before_score),
      after_score: reflectionForm.after_score.trim() === '' ? 0.5 : Number(reflectionForm.after_score),
      reflection_magnitude: reflectionForm.reflection_magnitude.trim() === '' ? 0 : Number(reflectionForm.reflection_magnitude),
    };
    if (reflectionForm.notes) payload.notes = reflectionForm.notes.trim();
    try {
      await api.cognitiveSymmetry.recordReflection(payload);
      toast.success('Reflection recorded');
      setReflectionForm({
        agent_id: '',
        axis: 'EMOTION',
        asymmetry_source: 'HABIT',
        before_score: '',
        after_score: '',
        reflection_magnitude: '',
        notes: '',
      });
      await loadReflections();
    } catch (e: any) { toast.error(e.message); }
  };

  // Take a new symmetry snapshot for the given agent.
  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveSymmetry.takeSnapshot(payload);
      // Surface the raw response inline so the operator can see what was captured.
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  // Create a new correction plan for an agent.
  const handlePlanCorrection = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_symmetry: planForm.target_symmetry.trim() === '' ? 0 : Number(planForm.target_symmetry),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveSymmetry.planCorrection(payload);
      toast.success('Correction plan created');
      setPlanForm({
        agent_id: '',
        strategy: 'BALANCE',
        target_symmetry: '',
        rationale: '',
      });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  // Record an alignment (final symmetry lock-in) event.
  const handleRecordAlignment = async () => {
    if (!alignmentForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: alignmentForm.agent_id.trim(),
      from_stage: alignmentForm.from_stage,
      to_stage: alignmentForm.to_stage,
      interval_ms: alignmentForm.interval_ms.trim() === '' ? 0 : Number(alignmentForm.interval_ms),
      signature: alignmentForm.signature.trim(),
    };
    if (alignmentForm.notes) payload.notes = alignmentForm.notes.trim();
    try {
      await api.cognitiveSymmetry.recordAlignment(payload);
      toast.success('Alignment recorded');
      setAlignmentForm({
        agent_id: '',
        from_stage: 'BROKEN',
        to_stage: 'TILTING',
        interval_ms: '',
        signature: '',
        notes: '',
      });
      await loadAlignments();
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
          <h2>🪞 Cognitive Symmetry</h2>
          <p className="panel-subtitle">
            Record symmetry readings, log reflections, and plan correction strategies across the cognitive symmetry engine
          </p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading cognitive symmetry...</span>
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
        <h2>🪞 Cognitive Symmetry</h2>
        <p className="panel-subtitle">
          Record symmetry readings, log reflections, and plan correction strategies across the cognitive symmetry engine
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_reflections ?? '-'}</span>
              <span className="stat-label">Reflections</span>
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
              <span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_alignments ?? '-'}</span>
              <span className="stat-label">Alignments</span>
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
        {(['overview', 'readings', 'reflections', 'snapshots', 'plans', 'alignments'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Symmetry Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Reflections</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_reflections ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Alignments</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_alignments ?? 0}</div>
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
                          {typeof r.symmetry_score !== 'undefined' && renderBadge(`symmetry ${r.symmetry_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent reflections card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Reflections</h3>
            <button onClick={() => loadReflections()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {reflections.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No reflections recorded. Record one in the Reflections section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {reflections.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reflection_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reflection {id}{r.asymmetry_source ? ` · ${r.asymmetry_source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.asymmetry_source && renderBadge(r.asymmetry_source, themeColors.secondary)}
                          {typeof r.before_score !== 'undefined' && typeof r.after_score !== 'undefined' && renderBadge(`${r.before_score}->${r.after_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent alignments card. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Alignments</h3>
            <button onClick={() => loadAlignments()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {alignments.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No alignments recorded. Record one in the Alignments section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {alignments.slice(0, 10).map((a: any, i: number) => {
                  const id = a.alignment_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>alignment {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.from_stage && renderBadge(a.from_stage, stageColor(a.from_stage))}
                          {a.to_stage && renderBadge(a.to_stage, stageColor(a.to_stage))}
                          {a.signature && renderBadge(a.signature, themeColors.secondary)}
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
                <label>Asymmetry Source</label>
                <select
                  className="form-select"
                  value={readingForm.asymmetry_source}
                  onChange={e => setReadingForm({ ...readingForm, asymmetry_source: e.target.value })}
                >
                  {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Symmetry Score</label>
                <input
                  className="form-input"
                  value={readingForm.symmetry_score}
                  onChange={e => setReadingForm({ ...readingForm, symmetry_score: e.target.value })}
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
                          {typeof r.symmetry_score !== 'undefined' && renderBadge(`symmetry ${r.symmetry_score}`, themeColors.primary)}
                          {r.asymmetry_source && renderBadge(r.asymmetry_source, themeColors.secondary)}
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

      {/* Reflections Section: form to record + list of recent reflections. */}
      {activeSection === 'reflections' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reflection</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={reflectionForm.agent_id}
                  onChange={e => setReflectionForm({ ...reflectionForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select
                  className="form-select"
                  value={reflectionForm.axis}
                  onChange={e => setReflectionForm({ ...reflectionForm, axis: e.target.value })}
                >
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Asymmetry Source</label>
                <select
                  className="form-select"
                  value={reflectionForm.asymmetry_source}
                  onChange={e => setReflectionForm({ ...reflectionForm, asymmetry_source: e.target.value })}
                >
                  {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Before Score</label>
                <input
                  className="form-input"
                  value={reflectionForm.before_score}
                  onChange={e => setReflectionForm({ ...reflectionForm, before_score: e.target.value })}
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
                  value={reflectionForm.after_score}
                  onChange={e => setReflectionForm({ ...reflectionForm, after_score: e.target.value })}
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  placeholder="e.g. 0.7"
                />
              </div>
              <div className="form-group">
                <label>Reflection Magnitude</label>
                <input
                  className="form-input"
                  value={reflectionForm.reflection_magnitude}
                  onChange={e => setReflectionForm({ ...reflectionForm, reflection_magnitude: e.target.value })}
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
                  value={reflectionForm.notes}
                  onChange={e => setReflectionForm({ ...reflectionForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordReflection}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Reflection
            </button>
          </div>

          {/* List of recent reflections, capped at 30 entries. */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Reflections ({reflections.length})</h3>
            <button
              onClick={() => loadReflections()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {reflections.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No reflections recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {reflections.slice(0, 30).map((r: any, i: number) => {
                  const id = r.reflection_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reflection {id}{r.asymmetry_source ? ` · ${r.asymmetry_source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {r.asymmetry_source && renderBadge(r.asymmetry_source, themeColors.secondary)}
                          {typeof r.before_score !== 'undefined' && typeof r.after_score !== 'undefined' && renderBadge(`${r.before_score}->${r.after_score}`, themeColors.primary)}
                          {typeof r.reflection_magnitude !== 'undefined' && renderBadge(`mag ${r.reflection_magnitude}`, themeColors.secondary)}
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
                          {typeof s.symmetry_score !== 'undefined' && renderBadge(`symmetry ${s.symmetry_score}`, themeColors.primary)}
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

      {/* Plans Section: form to plan a correction + list of recent plans. */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Correction</h3>
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
                <label>Target Symmetry</label>
                <input
                  className="form-input"
                  value={planForm.target_symmetry}
                  onChange={e => setPlanForm({ ...planForm, target_symmetry: e.target.value })}
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
              onClick={handlePlanCorrection}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Plan Correction
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
                          {typeof p.target_symmetry !== 'undefined' && renderBadge(`target ${p.target_symmetry}`, themeColors.primary)}
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

      {/* Alignments Section: form to record an alignment event + list of recent alignments. */}
      {activeSection === 'alignments' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Alignment</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  className="form-input"
                  value={alignmentForm.agent_id}
                  onChange={e => setAlignmentForm({ ...alignmentForm, agent_id: e.target.value })}
                  placeholder="agent id"
                />
              </div>
              <div className="form-group">
                <label>From Stage</label>
                <select
                  className="form-select"
                  value={alignmentForm.from_stage}
                  onChange={e => setAlignmentForm({ ...alignmentForm, from_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Stage</label>
                <select
                  className="form-select"
                  value={alignmentForm.to_stage}
                  onChange={e => setAlignmentForm({ ...alignmentForm, to_stage: e.target.value })}
                >
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Interval (ms)</label>
                <input
                  className="form-input"
                  value={alignmentForm.interval_ms}
                  onChange={e => setAlignmentForm({ ...alignmentForm, interval_ms: e.target.value })}
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
                  value={alignmentForm.signature}
                  onChange={e => setAlignmentForm({ ...alignmentForm, signature: e.target.value })}
                  placeholder="signature identifier"
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input
                  className="form-input"
                  value={alignmentForm.notes}
                  onChange={e => setAlignmentForm({ ...alignmentForm, notes: e.target.value })}
                  placeholder="optional notes"
                />
              </div>
            </div>
            <button
              onClick={handleRecordAlignment}
              className="btn-primary"
              style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}
            >
              Record Alignment
            </button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Alignments ({alignments.length})</h3>
            <button
              onClick={() => loadAlignments()}
              className="btn-sm"
              style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}
            >
              Refresh
            </button>
            {alignments.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No alignments recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {alignments.slice(0, 30).map((a: any, i: number) => {
                  const id = a.alignment_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>alignment {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.from_stage && renderBadge(a.from_stage, stageColor(a.from_stage))}
                          {a.to_stage && renderBadge(a.to_stage, stageColor(a.to_stage))}
                          {typeof a.interval_ms !== 'undefined' && renderBadge(`${a.interval_ms}ms`, themeColors.secondary)}
                          {a.signature && renderBadge(a.signature, themeColors.primary)}
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
export default CognitiveSymmetryPanel;
