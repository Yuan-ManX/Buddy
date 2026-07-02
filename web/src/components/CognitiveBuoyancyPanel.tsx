import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: indigo for cognitive buoyancy
const themeColors = {
  primary: '#4f46e5',
  secondary: '#6366f1',
  bg: '#eef2ff',
  border: '#c7d2fe',
  accent: '#e0e7ff',
  text: '#312e81',
};

// Enum values must match backend BuoyancyForce / BuoyancyRegime / VerticalLayer / LiftStrategy / SinkStrategy exactly (uppercase).
const BUOYANCY_FORCES = ['RELEVANCE', 'NOVELTY', 'EMOTIONAL_CHARGE', 'REPETITION', 'DENSITY', 'AGE', 'CONFIRMATION'];
const BUOYANCY_REGIMES = ['SINKING', 'NEUTRAL', 'FLOATING', 'BURSTING', 'STABLE_STRATIFIED'];
const VERTICAL_LAYERS = ['SURFACE', 'SHALLOW', 'MIDDLE', 'DEEP', 'ABYSSAL'];
const LIFT_STRATEGIES = ['EMPHASIZE', 'REPEAT', 'CONNECT', 'EMOTIONALIZE', 'SIMPLIFY', 'ANCHOR'];
const SINK_STRATEGIES = ['DEFER', 'ARCHIVE', 'ABSTRACT', 'SUPPRESS', 'COMPRESS', 'ROTATE'];

// Map a buoyancy regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  SINKING: '#dc2626',
  NEUTRAL: '#9ca3af',
  FLOATING: '#4f46e5',
  BURSTING: '#16a34a',
  STABLE_STRATIFIED: '#0ea5e9',
};

export const CognitiveBuoyancyPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reading' | 'movement' | 'plan'>('overview');

  // Readings / movements / lifts / sinks
  const [readings, setReadings] = useState<any[]>([]);
  const [movements, setMovements] = useState<any[]>([]);
  const [lifts, setLifts] = useState<any[]>([]);
  const [sinks, setSinks] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Read buoyancy form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    idea_label: '',
    force: 'RELEVANCE',
    buoyancy_score: '',
    current_layer: 'SURFACE',
  });

  // Record movement form
  const [movementForm, setMovementForm] = useState({
    agent_id: '',
    idea_label: '',
    from_layer: 'SURFACE',
    to_layer: 'SHALLOW',
    velocity: '',
  });

  // Plan lift form
  const [liftForm, setLiftForm] = useState({
    agent_id: '',
    idea_label: '',
    strategy: 'EMPHASIZE',
    rationale: '',
    expected_lift: '',
  });

  // Plan sink form
  const [sinkForm, setSinkForm] = useState({
    agent_id: '',
    idea_label: '',
    strategy: 'DEFER',
    rationale: '',
    expected_sink: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveBuoyancy.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive buoyancy stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveBuoyancy.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadMovements = async () => {
    try {
      const result = await api.cognitiveBuoyancy.listMovements();
      const list = Array.isArray(result) ? result : (result?.movements ?? []);
      setMovements(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load movements');
    }
  };

  const loadLifts = async () => {
    try {
      const result = await api.cognitiveBuoyancy.listLifts();
      const list = Array.isArray(result) ? result : (result?.lifts ?? []);
      setLifts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load lifts');
    }
  };

  const loadSinks = async () => {
    try {
      const result = await api.cognitiveBuoyancy.listSinks();
      const list = Array.isArray(result) ? result : (result?.sinks ?? []);
      setSinks(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load sinks');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadMovements();
      loadLifts();
      loadSinks();
    }
  }, [activeSection]);

  const handleReadBuoyancy = async () => {
    if (!readingForm.agent_id.trim() || !readingForm.idea_label.trim()) {
      toast.error('Agent ID and idea label are required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      idea_label: readingForm.idea_label.trim(),
      force: readingForm.force,
      current_layer: readingForm.current_layer,
    };
    if (readingForm.buoyancy_score.trim()) payload.buoyancy_score = Number(readingForm.buoyancy_score);
    try {
      await api.cognitiveBuoyancy.readBuoyancy(payload);
      toast.success('Buoyancy reading recorded');
      setReadingForm({ agent_id: '', idea_label: '', force: 'RELEVANCE', buoyancy_score: '', current_layer: 'SURFACE' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordMovement = async () => {
    if (!movementForm.agent_id.trim() || !movementForm.idea_label.trim()) {
      toast.error('Agent ID and idea label are required');
      return;
    }
    const payload: any = {
      agent_id: movementForm.agent_id.trim(),
      idea_label: movementForm.idea_label.trim(),
      from_layer: movementForm.from_layer,
      to_layer: movementForm.to_layer,
    };
    if (movementForm.velocity.trim()) payload.velocity = Number(movementForm.velocity);
    try {
      await api.cognitiveBuoyancy.recordMovement(payload);
      toast.success('Movement recorded');
      setMovementForm({ agent_id: '', idea_label: '', from_layer: 'SURFACE', to_layer: 'SHALLOW', velocity: '' });
      await loadMovements();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanLift = async () => {
    if (!liftForm.agent_id.trim() || !liftForm.idea_label.trim()) {
      toast.error('Agent ID and idea label are required');
      return;
    }
    const payload: any = {
      agent_id: liftForm.agent_id.trim(),
      idea_label: liftForm.idea_label.trim(),
      strategy: liftForm.strategy,
      rationale: liftForm.rationale.trim(),
    };
    if (liftForm.expected_lift.trim()) payload.expected_lift = Number(liftForm.expected_lift);
    try {
      await api.cognitiveBuoyancy.planLift(payload);
      toast.success('Lift planned');
      setLiftForm({ agent_id: '', idea_label: '', strategy: 'EMPHASIZE', rationale: '', expected_lift: '' });
      await loadLifts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanSink = async () => {
    if (!sinkForm.agent_id.trim() || !sinkForm.idea_label.trim()) {
      toast.error('Agent ID and idea label are required');
      return;
    }
    const payload: any = {
      agent_id: sinkForm.agent_id.trim(),
      idea_label: sinkForm.idea_label.trim(),
      strategy: sinkForm.strategy,
      rationale: sinkForm.rationale.trim(),
    };
    if (sinkForm.expected_sink.trim()) payload.expected_sink = Number(sinkForm.expected_sink);
    try {
      await api.cognitiveBuoyancy.planSink(payload);
      toast.success('Sink planned');
      setSinkForm({ agent_id: '', idea_label: '', strategy: 'DEFER', rationale: '', expected_sink: '' });
      await loadSinks();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required to take a snapshot');
      return;
    }
    try {
      const result = await api.cognitiveBuoyancy.takeSnapshot({ agent_id: readingForm.agent_id.trim() });
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadStats();
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
          <h2>🎈 Cognitive Buoyancy</h2>
          <p className="panel-subtitle">Read buoyancy, record movements, and plan lift or sink strategies across the cognitive strata</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive buoyancy...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🎈 Cognitive Buoyancy</h2>
        <p className="panel-subtitle">Read buoyancy, record movements, and plan lift or sink strategies across the cognitive strata</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_movements ?? '-'}</span><span className="stat-label">Movements</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_lifts ?? '-'}</span><span className="stat-label">Lifts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_sinks ?? '-'}</span><span className="stat-label">Sinks</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_buoyancy ?? '-'}</span><span className="stat-label">Avg Buoyancy</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reading', 'movement', 'plan'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Buoyancy Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Readings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_readings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Movements</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_movements ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Lifts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_lifts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Sinks</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_sinks ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Buoyancy</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_buoyancy ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Readings</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one in the Reading section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.idea_label ? ` · ${r.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.force && renderBadge(r.force, themeColors.secondary)}
                          {r.current_layer && renderBadge(r.current_layer, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginTop: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Movements</h3>
            <button onClick={() => loadMovements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {movements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No movements recorded. Record one in the Movement section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {movements.slice(0, 10).map((m: any, i: number) => {
                  const id = m.event_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>movement {id}{m.idea_label ? ` · ${m.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.from_layer && renderBadge(`from ${m.from_layer}`, themeColors.secondary)}
                          {m.to_layer && renderBadge(`to ${m.to_layer}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginTop: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Lifts</h3>
            <button onClick={() => loadLifts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {lifts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No lifts planned. Plan one in the Plan section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {lifts.slice(0, 10).map((l: any, i: number) => {
                  const id = l.plan_id ?? l.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {l.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>lift {id}{l.idea_label ? ` · ${l.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {l.strategy && renderBadge(l.strategy, themeColors.secondary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginTop: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Sinks</h3>
            <button onClick={() => loadSinks()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {sinks.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No sinks planned. Plan one in the Plan section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {sinks.slice(0, 10).map((s: any, i: number) => {
                  const id = s.plan_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>sink {id}{s.idea_label ? ` · ${s.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.strategy && renderBadge(s.strategy, themeColors.secondary)}
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

      {/* Reading Section */}
      {activeSection === 'reading' && (
        <div className="dashboard-section">
          {/* Read Buoyancy */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Read Buoyancy</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Force</label>
                <select className="form-select" value={readingForm.force} onChange={e => setReadingForm({ ...readingForm, force: e.target.value })}>
                  {BUOYANCY_FORCES.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Buoyancy Score</label>
                <input className="form-input" value={readingForm.buoyancy_score} onChange={e => setReadingForm({ ...readingForm, buoyancy_score: e.target.value })} type="number" min="-1" max="1" step="0.01" placeholder="-1 to 1 (positive floats, negative sinks)" />
              </div>
              <div className="form-group">
                <label>Current Layer</label>
                <select className="form-select" value={readingForm.current_layer} onChange={e => setReadingForm({ ...readingForm, current_layer: e.target.value })}>
                  {VERTICAL_LAYERS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Idea Label *</label>
                <input className="form-input" value={readingForm.idea_label} onChange={e => setReadingForm({ ...readingForm, idea_label: e.target.value })} placeholder="e.g. project deadline reminder" />
              </div>
            </div>
            <div className="form-row" style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button onClick={handleReadBuoyancy} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Read Buoyancy</button>
              <button onClick={handleTakeSnapshot} className="btn-sm" style={{ background: themeColors.secondary, color: '#fff' }}>Take Snapshot</button>
            </div>
            {snapshotResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(snapshotResult, null, 2)}</pre>
            )}
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.idea_label ? ` · ${r.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.force && renderBadge(r.force, themeColors.secondary)}
                          {r.current_layer && renderBadge(r.current_layer, themeColors.primary)}
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

      {/* Movement Section */}
      {activeSection === 'movement' && (
        <div className="dashboard-section">
          {/* Record Movement */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Movement</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={movementForm.agent_id} onChange={e => setMovementForm({ ...movementForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>From Layer</label>
                <select className="form-select" value={movementForm.from_layer} onChange={e => setMovementForm({ ...movementForm, from_layer: e.target.value })}>
                  {VERTICAL_LAYERS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Layer</label>
                <select className="form-select" value={movementForm.to_layer} onChange={e => setMovementForm({ ...movementForm, to_layer: e.target.value })}>
                  {VERTICAL_LAYERS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Velocity</label>
                <input className="form-input" value={movementForm.velocity} onChange={e => setMovementForm({ ...movementForm, velocity: e.target.value })} type="number" step="0.01" placeholder="positive=ascending, negative=descending" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Idea Label *</label>
                <input className="form-input" value={movementForm.idea_label} onChange={e => setMovementForm({ ...movementForm, idea_label: e.target.value })} placeholder="idea label" />
              </div>
            </div>
            <button onClick={handleRecordMovement} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Movement</button>
          </div>

          {/* Movements List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Movements ({movements.length})</h3>
            <button onClick={() => loadMovements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {movements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No movements recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {movements.slice(0, 30).map((m: any, i: number) => {
                  const id = m.event_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>movement {id}{m.idea_label ? ` · ${m.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.from_layer && renderBadge(`from ${m.from_layer}`, themeColors.secondary)}
                          {m.to_layer && renderBadge(`to ${m.to_layer}`, themeColors.primary)}
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

      {/* Plan Section */}
      {activeSection === 'plan' && (
        <div className="dashboard-section">
          {/* Plan Lift */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Lift</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={liftForm.agent_id} onChange={e => setLiftForm({ ...liftForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={liftForm.strategy} onChange={e => setLiftForm({ ...liftForm, strategy: e.target.value })}>
                  {LIFT_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Lift</label>
                <input className="form-input" value={liftForm.expected_lift} onChange={e => setLiftForm({ ...liftForm, expected_lift: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Idea Label *</label>
                <input className="form-input" value={liftForm.idea_label} onChange={e => setLiftForm({ ...liftForm, idea_label: e.target.value })} placeholder="idea label" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={liftForm.rationale} onChange={e => setLiftForm({ ...liftForm, rationale: e.target.value })} placeholder="why this lift strategy" />
              </div>
            </div>
            <button onClick={handlePlanLift} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Lift</button>
          </div>

          {/* Plan Sink */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Sink</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={sinkForm.agent_id} onChange={e => setSinkForm({ ...sinkForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={sinkForm.strategy} onChange={e => setSinkForm({ ...sinkForm, strategy: e.target.value })}>
                  {SINK_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Sink</label>
                <input className="form-input" value={sinkForm.expected_sink} onChange={e => setSinkForm({ ...sinkForm, expected_sink: e.target.value })} type="number" step="0.01" placeholder="e.g. -0.3" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Idea Label *</label>
                <input className="form-input" value={sinkForm.idea_label} onChange={e => setSinkForm({ ...sinkForm, idea_label: e.target.value })} placeholder="idea label" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={sinkForm.rationale} onChange={e => setSinkForm({ ...sinkForm, rationale: e.target.value })} placeholder="why this sink strategy" />
              </div>
            </div>
            <button onClick={handlePlanSink} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Sink</button>
          </div>

          {/* Lifts List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Lifts ({lifts.length})</h3>
            <button onClick={() => loadLifts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {lifts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No lifts planned. Plan one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {lifts.slice(0, 30).map((l: any, i: number) => {
                  const id = l.plan_id ?? l.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {l.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>lift {id}{l.idea_label ? ` · ${l.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {l.strategy && renderBadge(l.strategy, themeColors.secondary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Sinks List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Sinks ({sinks.length})</h3>
            <button onClick={() => loadSinks()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {sinks.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No sinks planned. Plan one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {sinks.slice(0, 30).map((s: any, i: number) => {
                  const id = s.plan_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>sink {id}{s.idea_label ? ` · ${s.idea_label}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.strategy && renderBadge(s.strategy, themeColors.secondary)}
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

export default CognitiveBuoyancyPanel;
