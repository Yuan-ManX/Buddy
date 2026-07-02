// CognitivePermeabilityPanel.tsx
//
// Frontend panel for the cognitive permeability engine. Provides an interactive
// UI for recording permeability readings, logging transits, taking membrane
// snapshots, planning permeability adjustments, and tracking flow events.
//
// This panel mirrors the layout and conventions of the other cognitive
// subsystem panels (e.g. CognitiveCadencePanel) so that operators have a
// consistent experience across the dashboard. The theme uses emerald / green
// tones to suggest a permeable, growth-oriented membrane.

import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ---------------------------------------------------------------------------
// Theme palette (emerald / green tones for permeability).
// These colors are reused throughout the panel for headers, borders, badges
// and the active tab indicator. Keeping them in one object makes it trivial
// to retheme the panel in the future.
// ---------------------------------------------------------------------------
const themeColors = {
  primary: '#059669',
  secondary: '#10b981',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

// ---------------------------------------------------------------------------
// Enumerations.
//
// The strings in these constants MUST match the backend enum values
// exactly (uppercase). If the backend ever renames an enum, the change
// must be mirrored here. The backend enums define the universe of legal
// values that the server will accept and return.
// ---------------------------------------------------------------------------

// Cognitive axes the membrane spans. Each axis represents a different
// dimension of cognition that can be permeated or shielded.
const AXES = ['LOGIC', 'EMOTION', 'MEMORY', 'PERCEPTION', 'ACTION', 'SELF'];

// Permeability regimes describe how open or closed the membrane currently is.
// HERMETIC is fully sealed; OPEN is fully permeable. Intermediate regimes
// represent gradient states of selectivity.
const REGIMES = ['HERMETIC', 'SEALED', 'FILTERED', 'SELECTIVE', 'POROUS', 'OPEN'];

// Direction of a transit event across the membrane.
const DIRECTIONS = ['INBOUND', 'OUTBOUND', 'BIDIRECTIONAL', 'BLOCKED', 'REFLECTED', 'ABSORBED'];

// Strategies that can be applied to plan a membrane adjustment.
const STRATEGIES = ['HARDEN', 'FILTER', 'ADMIT', 'GATE', 'REPLACE', 'DISSOLVE'];

// Lifecycle stages a flow event moves through as it traverses the membrane.
const STAGES = ['CLOSED', 'PRESSURIZING', 'ADMITTING', 'FLOWING', 'SETTLING', 'DRAINED'];

// ---------------------------------------------------------------------------
// Status color mapping.
//
// Map a regime value to a badge color so users can scan the dashboard and
// quickly see whether a given record is more closed (cool/warm colors) or
// open (greens) at a glance. The mapping is deliberately limited to the
// official regime values.
// ---------------------------------------------------------------------------
const REGIME_COLORS: Record<string, string> = {
  HERMETIC: '#374151',
  SEALED: '#4b5563',
  FILTERED: '#0ea5e9',
  SELECTIVE: '#6366f1',
  POROUS: '#10b981',
  OPEN: '#16a34a',
};

// Map a transit direction to a color so transits can be read at a glance.
const DIRECTION_COLORS: Record<string, string> = {
  INBOUND: '#0ea5e9',
  OUTBOUND: '#f59e0b',
  BIDIRECTIONAL: '#10b981',
  BLOCKED: '#dc2626',
  REFLECTED: '#a855f7',
  ABSORBED: '#16a34a',
};

// Map a flow stage to a color so flow state can be read at a glance.
const STAGE_COLORS: Record<string, string> = {
  CLOSED: '#6b7280',
  PRESSURIZING: '#0ea5e9',
  ADMITTING: '#10b981',
  FLOWING: '#16a34a',
  SETTLING: '#a855f7',
  DRAINED: '#4b5563',
};

// ---------------------------------------------------------------------------
// Main panel component.
// ---------------------------------------------------------------------------
export const CognitivePermeabilityPanel: React.FC = () => {
  // Toast helper for surfacing success / failure messages to the user.
  const toast = useToast();

  // Top-level state.
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Currently active section tab. Drives which content is rendered.
  const [activeSection, setActiveSection] = useState<
    'overview' | 'readings' | 'transits' | 'snapshots' | 'plans' | 'flows'
  >('overview');

  // Collections of records fetched from the backend.
  const [readings, setReadings] = useState<any[]>([]);
  const [transits, setTransits] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [flows, setFlows] = useState<any[]>([]);
  // Holds the most recent snapshot response so users can inspect its details.
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // -------------------------------------------------------------------------
  // Form state.
  // Each form is held in its own object so resetting is trivial.
  // -------------------------------------------------------------------------

  // Form for recording a permeability reading.
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'LOGIC',
    regime: 'SELECTIVE',
    permeability: '',
    selectivity_score: '',
    notes: '',
  });

  // Form for recording a transit (a single traversal of the membrane).
  const [transitForm, setTransitForm] = useState({
    agent_id: '',
    axis: 'LOGIC',
    direction: 'INBOUND',
    payload_size: '',
    accepted: 'true',
    notes: '',
  });

  // Form for taking a membrane snapshot. Just needs the agent id.
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Form for planning a membrane adjustment.
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    axis: 'LOGIC',
    strategy: 'FILTER',
    target_regime: 'SELECTIVE',
    rationale: '',
  });

  // Form for recording a flow event.
  const [flowForm, setFlowForm] = useState({
    agent_id: '',
    axis: 'LOGIC',
    stage: 'PRESSURIZING',
    flux: '',
    notes: '',
  });

  // -------------------------------------------------------------------------
  // Data loaders. Each function fetches a single resource, normalises the
  // payload (it may be a bare array or an object containing an array) and
  // writes the result into the relevant state slot.
  // -------------------------------------------------------------------------

  // Load aggregate statistics for the cognitive permeability engine.
  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitivePermeability.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive permeability stats');
    } finally {
      setLoading(false);
    }
  };

  // Load the list of permeability readings.
  const loadReadings = async () => {
    try {
      const result = await api.cognitivePermeability.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  // Load the list of transit events.
  const loadTransits = async () => {
    try {
      const result = await api.cognitivePermeability.listTransits();
      const list = Array.isArray(result) ? result : (result?.transits ?? []);
      setTransits(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load transits');
    }
  };

  // Load the list of membrane snapshots.
  const loadSnapshots = async () => {
    try {
      const result = await api.cognitivePermeability.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  // Load the list of permeability plans.
  const loadPlans = async () => {
    try {
      const result = await api.cognitivePermeability.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  // Load the list of flow events.
  const loadFlows = async () => {
    try {
      const result = await api.cognitivePermeability.listFlows();
      const list = Array.isArray(result) ? result : (result?.flows ?? []);
      setFlows(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load flows');
    }
  };

  // -------------------------------------------------------------------------
  // Effects. Initial load on mount, and a heavier reload whenever the user
  // switches to the overview tab so the dashboard always feels fresh.
  // -------------------------------------------------------------------------

  // Load stats once on mount.
  useEffect(() => {
    loadStats();
  }, []);

  // When the user enters the overview tab, refresh all the lists.
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadTransits();
      loadSnapshots();
      loadPlans();
      loadFlows();
    }
  }, [activeSection]);

  // -------------------------------------------------------------------------
  // Submit handlers. Each handler validates its form, builds the payload,
  // calls the relevant API method, refreshes the corresponding list and
  // surfaces feedback via the toast helper.
  // -------------------------------------------------------------------------

  // Submit the record-reading form.
  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    // Build the payload; use safe defaults for blank numeric fields.
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      regime: readingForm.regime,
      permeability: readingForm.permeability.trim() === '' ? 0.5 : Number(readingForm.permeability),
      selectivity_score: readingForm.selectivity_score.trim() === '' ? 0.5 : Number(readingForm.selectivity_score),
    };
    // Only include optional fields if they have content.
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitivePermeability.recordReading(payload);
      toast.success('Reading recorded');
      // Reset form to its defaults.
      setReadingForm({ agent_id: '', axis: 'LOGIC', regime: 'SELECTIVE', permeability: '', selectivity_score: '', notes: '' });
      await loadReadings();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // Submit the record-transit form.
  const handleRecordTransit = async () => {
    if (!transitForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: transitForm.agent_id.trim(),
      axis: transitForm.axis,
      direction: transitForm.direction,
      payload_size: transitForm.payload_size.trim() === '' ? 0 : Number(transitForm.payload_size),
      accepted: transitForm.accepted === 'true',
    };
    if (transitForm.notes) payload.notes = transitForm.notes.trim();
    try {
      await api.cognitivePermeability.recordTransit(payload);
      toast.success('Transit recorded');
      setTransitForm({ agent_id: '', axis: 'LOGIC', direction: 'INBOUND', payload_size: '', accepted: 'true', notes: '' });
      await loadTransits();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // Submit the take-snapshot form. Stores the result for inspection.
  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitivePermeability.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // Submit the plan-membrane form.
  const handlePlanMembrane = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      axis: planForm.axis,
      strategy: planForm.strategy,
      target_regime: planForm.target_regime,
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitivePermeability.planMembrane(payload);
      toast.success('Permeability plan created');
      setPlanForm({ agent_id: '', axis: 'LOGIC', strategy: 'FILTER', target_regime: 'SELECTIVE', rationale: '' });
      await loadPlans();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // Submit the record-flow form.
  const handleRecordFlow = async () => {
    if (!flowForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: flowForm.agent_id.trim(),
      axis: flowForm.axis,
      stage: flowForm.stage,
      flux: flowForm.flux.trim() === '' ? 0 : Number(flowForm.flux),
    };
    if (flowForm.notes) payload.notes = flowForm.notes.trim();
    try {
      await api.cognitivePermeability.recordFlow(payload);
      toast.success('Flow recorded');
      setFlowForm({ agent_id: '', axis: 'LOGIC', stage: 'PRESSURIZING', flux: '', notes: '' });
      await loadFlows();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // -------------------------------------------------------------------------
  // Small UI helpers.
  // -------------------------------------------------------------------------

  // Render a small rounded badge. Used throughout the panel to label records
  // with their key attribute values.
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

  // Resolve a regime string to its color, falling back to the primary color.
  const regimeColor = (r: string) => REGIME_COLORS[r] ?? themeColors.primary;
  // Resolve a direction string to its color, falling back to the primary color.
  const directionColor = (d: string) => DIRECTION_COLORS[d] ?? themeColors.primary;
  // Resolve a stage string to its color, falling back to the primary color.
  const stageColor = (s: string) => STAGE_COLORS[s] ?? themeColors.primary;

  // -------------------------------------------------------------------------
  // Loading state. While the initial stats request is in flight we render a
  // lightweight loading placeholder so the page does not jump around.
  // -------------------------------------------------------------------------
  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🌿 Cognitive Permeability</h2>
          <p className="panel-subtitle">Track how the cognitive membrane admits, filters, and sheds information across agents</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading cognitive permeability...</span>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Main render.
  // -------------------------------------------------------------------------
  return (
    <div
      className="panel-container"
      style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}
    >
      {/* Header */}
      <div className="panel-header">
        <h2>🌿 Cognitive Permeability</h2>
        <p className="panel-subtitle">Track how the cognitive membrane admits, filters, and sheds information across agents</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats bar — a row of high-level numbers summarising the engine. */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_transits ?? '-'}</span><span className="stat-label">Transits</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_plans ?? '-'}</span><span className="stat-label">Plans</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_flows ?? '-'}</span><span className="stat-label">Flows</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section tabs. The user can switch between the dashboard and the
          individual collection pages from here. */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'transits', 'snapshots', 'plans', 'flows'] as const).map(s => (
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

      {/* =================================================================
          OVERVIEW SECTION
          A dashboard view that summarises the most recent records across
          every collection. Used as the landing tab.
          ================================================================= */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          {/* High-level metric cards */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Permeability Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Transits</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_transits ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Flows</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_flows ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dominant Regime</div>
                <div style={{ fontSize: 18, color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</div>
              </div>
            </div>
          </div>

          {/* Recent readings preview */}
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
                          {typeof r.permeability !== 'undefined' && renderBadge(`perm ${r.permeability}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent transits preview */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Transits</h3>
            <button onClick={() => loadTransits()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {transits.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No transits logged. Record one in the Transits section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {transits.slice(0, 10).map((t: any, i: number) => {
                  const id = t.transit_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {t.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>transit {id}{t.axis ? ` · ${t.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {t.axis && renderBadge(t.axis, themeColors.secondary)}
                          {t.direction && renderBadge(t.direction, directionColor(t.direction))}
                          {typeof t.accepted !== 'undefined' && renderBadge(t.accepted ? 'accepted' : 'rejected', t.accepted ? '#16a34a' : '#dc2626')}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent flows preview */}
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>flow {id}{f.axis ? ` · ${f.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.axis && renderBadge(f.axis, themeColors.secondary)}
                          {f.stage && renderBadge(f.stage, stageColor(f.stage))}
                          {typeof f.flux !== 'undefined' && renderBadge(`flux ${f.flux}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Snapshots and plans refresh buttons */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Snapshots &amp; Plans</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
              <button onClick={() => loadSnapshots()} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Refresh Snapshots ({snapshots.length})</button>
              <button onClick={() => loadPlans()} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Refresh Plans ({plans.length})</button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================
          READINGS SECTION
          Form for creating a new permeability reading plus the list of
          existing readings.
          ================================================================= */}
      {activeSection === 'readings' && (
        <div className="dashboard-section">
          {/* Record reading form */}
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
                <label>Permeability</label>
                <input className="form-input" value={readingForm.permeability} onChange={e => setReadingForm({ ...readingForm, permeability: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Selectivity Score</label>
                <input className="form-input" value={readingForm.selectivity_score} onChange={e => setReadingForm({ ...readingForm, selectivity_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={readingForm.notes} onChange={e => setReadingForm({ ...readingForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordReading} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reading</button>
          </div>

          {/* Readings list */}
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
                          {typeof r.permeability !== 'undefined' && renderBadge(`perm ${r.permeability}`, themeColors.primary)}
                          {typeof r.selectivity_score !== 'undefined' && renderBadge(`sel ${r.selectivity_score}`, themeColors.secondary)}
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

      {/* =================================================================
          TRANSITS SECTION
          Form for logging a new transit and the list of existing transits.
          ================================================================= */}
      {activeSection === 'transits' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Transit</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={transitForm.agent_id} onChange={e => setTransitForm({ ...transitForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={transitForm.axis} onChange={e => setTransitForm({ ...transitForm, axis: e.target.value })}>
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Direction</label>
                <select className="form-select" value={transitForm.direction} onChange={e => setTransitForm({ ...transitForm, direction: e.target.value })}>
                  {DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Payload Size</label>
                <input className="form-input" value={transitForm.payload_size} onChange={e => setTransitForm({ ...transitForm, payload_size: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 128" />
              </div>
              <div className="form-group">
                <label>Accepted</label>
                <select className="form-select" value={transitForm.accepted} onChange={e => setTransitForm({ ...transitForm, accepted: e.target.value })}>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={transitForm.notes} onChange={e => setTransitForm({ ...transitForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordTransit} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Transit</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Transits ({transits.length})</h3>
            <button onClick={() => loadTransits()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {transits.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No transits recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {transits.slice(0, 30).map((t: any, i: number) => {
                  const id = t.transit_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {t.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>transit {id}{t.axis ? ` · ${t.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {t.axis && renderBadge(t.axis, themeColors.secondary)}
                          {t.direction && renderBadge(t.direction, directionColor(t.direction))}
                          {typeof t.payload_size !== 'undefined' && renderBadge(`size ${t.payload_size}`, themeColors.primary)}
                          {typeof t.accepted !== 'undefined' && renderBadge(t.accepted ? 'accepted' : 'rejected', t.accepted ? '#16a34a' : '#dc2626')}
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

      {/* =================================================================
          SNAPSHOTS SECTION
          Take a snapshot of the current membrane state and inspect the
          recent snapshot history.
          ================================================================= */}
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
            {/* Show the most recent snapshot response in a collapsible JSON view. */}
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
                          {/* Show the dominant regime if present, otherwise show the first axis. */}
                          {s.regime && renderBadge(s.regime, regimeColor(s.regime))}
                          {s.axis && renderBadge(s.axis, themeColors.secondary)}
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

      {/* =================================================================
          PLANS SECTION
          Build a plan that adjusts the membrane from one regime to another
          and inspect the existing plan history.
          ================================================================= */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Membrane</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={planForm.axis} onChange={e => setPlanForm({ ...planForm, axis: e.target.value })}>
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Regime</label>
                <select className="form-select" value={planForm.target_regime} onChange={e => setPlanForm({ ...planForm, target_regime: e.target.value })}>
                  {REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="why this plan?" />
              </div>
            </div>
            <button onClick={handlePlanMembrane} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Membrane</button>
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
                          {p.axis && renderBadge(p.axis, themeColors.secondary)}
                          {p.strategy && renderBadge(p.strategy, themeColors.primary)}
                          {p.target_regime && renderBadge(`-> ${p.target_regime}`, regimeColor(p.target_regime))}
                        </div>
                      </div>
                      {p.rationale && <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 6 }}>{p.rationale}</div>}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* =================================================================
          FLOWS SECTION
          Record a flow event (a transit lifecycle observation) and review
          the flow history.
          ================================================================= */}
      {activeSection === 'flows' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Flow</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={flowForm.agent_id} onChange={e => setFlowForm({ ...flowForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={flowForm.axis} onChange={e => setFlowForm({ ...flowForm, axis: e.target.value })}>
                  {AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Stage</label>
                <select className="form-select" value={flowForm.stage} onChange={e => setFlowForm({ ...flowForm, stage: e.target.value })}>
                  {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Flux</label>
                <input className="form-input" value={flowForm.flux} onChange={e => setFlowForm({ ...flowForm, flux: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.42" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={flowForm.notes} onChange={e => setFlowForm({ ...flowForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordFlow} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Flow</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Flows ({flows.length})</h3>
            <button onClick={() => loadFlows()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>flow {id}{f.axis ? ` · ${f.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.axis && renderBadge(f.axis, themeColors.secondary)}
                          {f.stage && renderBadge(f.stage, stageColor(f.stage))}
                          {typeof f.flux !== 'undefined' && renderBadge(`flux ${f.flux}`, themeColors.primary)}
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

// Default export mirrors the named export so consumers can pick whichever
// import style suits them. Most other panels in this codebase use the named
// export, so we keep that as the primary form.
export default CognitivePermeabilityPanel;
