import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: amber for cognitive inertia
const themeColors = {
  primary: '#d97706',
  secondary: '#f59e0b',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

// Enum values must match backend MassType / InertiaRegime / MotionState / ForceStrategy / ResistanceSource exactly (uppercase).
const MASS_TYPES = ['CONCEPTUAL', 'EMOTIONAL', 'PROCEDURAL', 'CONTEXTUAL', 'STRUCTURAL', 'EPISTEMIC'];
const INERTIA_REGIMES = ['WEIGHTLESS', 'LIGHT', 'BALANCED', 'HEAVY', 'IMMOBILE', 'ANCHORED'];
const MOTION_STATES = ['STATIONARY', 'DRIFTING', 'STEADY', 'ACCELERATING', 'DECELERATING', 'OSCILLATING'];
const FORCE_STRATEGIES = ['PUSH', 'STEER', 'COUNTER', 'BRAKE', 'LEVER', 'DAMP'];
const RESISTANCE_SOURCES = ['HABIT', 'COMMITMENT', 'IDENTITY', 'INVESTMENT', 'STRUCTURAL', 'EMOTIONAL'];

// Map an inertia regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  WEIGHTLESS: '#06b6d4',
  LIGHT: '#0ea5e9',
  BALANCED: '#16a34a',
  HEAVY: '#f59e0b',
  IMMOBILE: '#ea580c',
  ANCHORED: '#dc2626',
};

export const CognitiveInertiaPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reading' | 'force'>('overview');

  // Readings / forces / motions / snapshot result
  const [readings, setReadings] = useState<any[]>([]);
  const [forces, setForces] = useState<any[]>([]);
  const [motions, setMotions] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    mass_type: 'CONCEPTUAL',
    mass_value: '',
    velocity: '',
    motion_state: 'STATIONARY',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Apply force form
  const [forceForm, setForceForm] = useState({
    agent_id: '',
    force_magnitude: '',
    direction: '',
    strategy: 'PUSH',
    source: 'HABIT',
  });

  // Record motion form
  const [motionForm, setMotionForm] = useState({
    agent_id: '',
    from_state: 'STATIONARY',
    to_state: 'DRIFTING',
    delta_velocity: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveInertia.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive inertia stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveInertia.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadForces = async () => {
    try {
      const result = await api.cognitiveInertia.listForces();
      const list = Array.isArray(result) ? result : (result?.forces ?? []);
      setForces(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load forces');
    }
  };

  const loadMotions = async () => {
    try {
      const result = await api.cognitiveInertia.listMotions();
      const list = Array.isArray(result) ? result : (result?.motions ?? []);
      setMotions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load motions');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); loadReadings(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadForces();
      loadMotions();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      mass_type: readingForm.mass_type,
      mass_value: readingForm.mass_value.trim() === '' ? 0.5 : Number(readingForm.mass_value),
      velocity: readingForm.velocity.trim() === '' ? 0 : Number(readingForm.velocity),
      motion_state: readingForm.motion_state,
    };
    try {
      await api.cognitiveInertia.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', mass_type: 'CONCEPTUAL', mass_value: '', velocity: '', motion_state: 'STATIONARY' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveInertia.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyForce = async () => {
    if (!forceForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: forceForm.agent_id.trim(),
      force_magnitude: forceForm.force_magnitude.trim() === '' ? 0.5 : Number(forceForm.force_magnitude),
      direction: forceForm.direction.trim() === '' ? 0 : Number(forceForm.direction),
      strategy: forceForm.strategy,
      source: forceForm.source,
    };
    try {
      await api.cognitiveInertia.applyForce(payload);
      toast.success('Force applied');
      setForceForm({ agent_id: '', force_magnitude: '', direction: '', strategy: 'PUSH', source: 'HABIT' });
      await loadForces();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordMotion = async () => {
    if (!motionForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: motionForm.agent_id.trim(),
      from_state: motionForm.from_state,
      to_state: motionForm.to_state,
      delta_velocity: motionForm.delta_velocity.trim() === '' ? 0 : Number(motionForm.delta_velocity),
    };
    try {
      await api.cognitiveInertia.recordMotion(payload);
      toast.success('Motion recorded');
      setMotionForm({ agent_id: '', from_state: 'STATIONARY', to_state: 'DRIFTING', delta_velocity: '' });
      await loadMotions();
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
          <h2>⚖️ Cognitive Inertia Engine</h2>
          <p className="panel-subtitle">Record inertia readings, apply forces, and track motion regimes across cognitive mass</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive inertia...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚖️ Cognitive Inertia Engine</h2>
        <p className="panel-subtitle">Record inertia readings, apply forces, and track motion regimes across cognitive mass</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Total Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_forces ?? '-'}</span><span className="stat-label">Forces</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_motions ?? '-'}</span><span className="stat-label">Motions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_inertia ?? '-'}</span><span className="stat-label">Avg Inertia</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reading', 'force'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Inertia Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Forces</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_forces ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Motions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_motions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Inertia</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_inertia ?? 0}</div>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.mass_type ? ` · ${r.mass_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.mass_type && renderBadge(r.mass_type, themeColors.secondary)}
                          {typeof r.mass_value !== 'undefined' && renderBadge(`mass ${r.mass_value}`, themeColors.primary)}
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Forces</h3>
            <button onClick={() => loadForces()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {forces.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No forces applied. Apply one in the Force section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {forces.slice(0, 10).map((f: any, i: number) => {
                  const id = f.application_id ?? f.force_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>force {id}{f.source ? ` · ${f.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.strategy && renderBadge(f.strategy, themeColors.secondary)}
                          {typeof f.force_magnitude !== 'undefined' && renderBadge(`mag ${f.force_magnitude}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Motions</h3>
            <button onClick={() => loadMotions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {motions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No motions recorded. Record one in the Force section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {motions.slice(0, 10).map((m: any, i: number) => {
                  const id = m.record_id ?? m.motion_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>motion {id}{m.from_state && m.to_state ? ` · ${m.from_state} → ${m.to_state}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.from_state && renderBadge(m.from_state, themeColors.secondary)}
                          {m.to_state && renderBadge(m.to_state, themeColors.primary)}
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
          {/* Record Reading */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reading</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Mass Type</label>
                <select className="form-select" value={readingForm.mass_type} onChange={e => setReadingForm({ ...readingForm, mass_type: e.target.value })}>
                  {MASS_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Mass Value</label>
                <input className="form-input" value={readingForm.mass_value} onChange={e => setReadingForm({ ...readingForm, mass_value: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>Velocity</label>
                <input className="form-input" value={readingForm.velocity} onChange={e => setReadingForm({ ...readingForm, velocity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.1" />
              </div>
              <div className="form-group">
                <label>Motion State</label>
                <select className="form-select" value={readingForm.motion_state} onChange={e => setReadingForm({ ...readingForm, motion_state: e.target.value })}>
                  {MOTION_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRecordReading} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reading</button>
          </div>

          {/* Take Snapshot */}
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.mass_type ? ` · ${r.mass_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.mass_type && renderBadge(r.mass_type, themeColors.secondary)}
                          {typeof r.mass_value !== 'undefined' && renderBadge(`mass ${r.mass_value}`, themeColors.primary)}
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
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

      {/* Force Section */}
      {activeSection === 'force' && (
        <div className="dashboard-section">
          {/* Apply Force */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Force</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={forceForm.agent_id} onChange={e => setForceForm({ ...forceForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Force Magnitude</label>
                <input className="form-input" value={forceForm.force_magnitude} onChange={e => setForceForm({ ...forceForm, force_magnitude: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>Direction</label>
                <input className="form-input" value={forceForm.direction} onChange={e => setForceForm({ ...forceForm, direction: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.0" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={forceForm.strategy} onChange={e => setForceForm({ ...forceForm, strategy: e.target.value })}>
                  {FORCE_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Source</label>
                <select className="form-select" value={forceForm.source} onChange={e => setForceForm({ ...forceForm, source: e.target.value })}>
                  {RESISTANCE_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleApplyForce} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Force</button>
          </div>

          {/* Record Motion */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Motion</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={motionForm.agent_id} onChange={e => setMotionForm({ ...motionForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>From State</label>
                <select className="form-select" value={motionForm.from_state} onChange={e => setMotionForm({ ...motionForm, from_state: e.target.value })}>
                  {MOTION_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To State</label>
                <select className="form-select" value={motionForm.to_state} onChange={e => setMotionForm({ ...motionForm, to_state: e.target.value })}>
                  {MOTION_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Delta Velocity</label>
                <input className="form-input" value={motionForm.delta_velocity} onChange={e => setMotionForm({ ...motionForm, delta_velocity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.1" />
              </div>
            </div>
            <button onClick={handleRecordMotion} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Motion</button>
          </div>

          {/* Forces List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Forces ({forces.length})</h3>
            <button onClick={() => loadForces()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {forces.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No forces applied. Apply one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {forces.slice(0, 30).map((f: any, i: number) => {
                  const id = f.application_id ?? f.force_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>force {id}{f.source ? ` · ${f.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.strategy && renderBadge(f.strategy, themeColors.secondary)}
                          {typeof f.force_magnitude !== 'undefined' && renderBadge(`mag ${f.force_magnitude}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Motions List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Motions ({motions.length})</h3>
            <button onClick={() => loadMotions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {motions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No motions recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {motions.slice(0, 30).map((m: any, i: number) => {
                  const id = m.record_id ?? m.motion_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>motion {id}{m.from_state && m.to_state ? ` · ${m.from_state} → ${m.to_state}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.from_state && renderBadge(m.from_state, themeColors.secondary)}
                          {m.to_state && renderBadge(m.to_state, themeColors.primary)}
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

export default CognitiveInertiaPanel;
