import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: orange for cognitive friction
const themeColors = {
  primary: '#ea580c',
  secondary: '#f97316',
  bg: '#fff7ed',
  border: '#fed7aa',
  accent: '#ffedd5',
  text: '#7c2d12',
};

// Enum values must match backend FrictionSource / FrictionRegime / TransitionType / LubricationStrategy / RecoveryState exactly (uppercase).
const FRICTION_SOURCES = ['ANCHORING', 'COMMITMENT', 'CONTEXT_SWITCH', 'ABSTRACTION_GAP', 'INCOMPATIBILITY', 'HABIT'];
const FRICTION_REGIMES = ['FLUID', 'SMOOTH', 'MODERATE', 'HIGH', 'FROZEN'];
const TRANSITION_TYPES = ['CONCEPT_SHIFT', 'BELIEF_REVISION', 'CONTEXT_PIVOT', 'ABSTRACTION_MOVE', 'PERSPECTIVE_SWITCH', 'GOAL_REDIRECT'];
const LUBRICATION_STRATEGIES = ['PRIME', 'CHUNK', 'BRIDGE', 'REFRAME', 'ANCHOR_RELEASE', 'EXTERNAL_PROMPT'];
const RECOVERY_STATES = ['FLOWING', 'SLUGGISH', 'STALLED', 'REVERSING', 'RECOVERED'];

// Map a friction regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  FLUID: '#16a34a',
  SMOOTH: '#0ea5e9',
  MODERATE: '#f59e0b',
  HIGH: '#f97316',
  FROZEN: '#dc2626',
};

export const CognitiveFrictionPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'measurement' | 'lubrication'>('overview');

  // Measurements / transitions / lubrications
  const [measurements, setMeasurements] = useState<any[]>([]);
  const [transitions, setTransitions] = useState<any[]>([]);
  const [lubrications, setLubrications] = useState<any[]>([]);
  const [recoveryResult, setRecoveryResult] = useState<any>(null);

  // Record measurement form
  const [measurementForm, setMeasurementForm] = useState({
    agent_id: '',
    source: 'ANCHORING',
    resistance_score: '',
    transition_type: 'CONCEPT_SHIFT',
    from_state: '',
    to_state: '',
  });

  // Record transition form
  const [transitionForm, setTransitionForm] = useState({
    agent_id: '',
    transition_type: 'CONCEPT_SHIFT',
    from_state: '',
    to_state: '',
    friction_score: '',
    duration: '',
  });

  // Plan lubrication form
  const [lubricationForm, setLubricationForm] = useState({
    agent_id: '',
    transition_id: '',
    strategy: 'PRIME',
    expected_relief: '',
  });

  // Assess recovery form
  const [recoveryForm, setRecoveryForm] = useState({
    agent_id: '',
    transition_id: '',
    from_state: 'STALLED',
    to_state: 'RECOVERED',
    strategy: 'PRIME',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveFriction.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive friction stats');
    } finally {
      setLoading(false);
    }
  };

  const loadMeasurements = async () => {
    try {
      const result = await api.cognitiveFriction.listMeasurements();
      const list = Array.isArray(result) ? result : (result?.measurements ?? []);
      setMeasurements(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load measurements');
    }
  };

  const loadTransitions = async () => {
    try {
      const result = await api.cognitiveFriction.listTransitions();
      const list = Array.isArray(result) ? result : (result?.transitions ?? []);
      setTransitions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load transitions');
    }
  };

  const loadLubrications = async () => {
    try {
      const result = await api.cognitiveFriction.listLubrications();
      const list = Array.isArray(result) ? result : (result?.lubrications ?? []);
      setLubrications(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load lubrications');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadMeasurements();
      loadTransitions();
      loadLubrications();
    }
  }, [activeSection]);

  const handleRecordMeasurement = async () => {
    if (!measurementForm.agent_id.trim() || !measurementForm.resistance_score.trim()) {
      toast.error('Agent ID and resistance score are required');
      return;
    }
    const payload: any = {
      agent_id: measurementForm.agent_id.trim(),
      source: measurementForm.source,
      resistance_score: Number(measurementForm.resistance_score),
      transition_type: measurementForm.transition_type,
    };
    if (measurementForm.from_state.trim()) payload.from_state = measurementForm.from_state.trim();
    if (measurementForm.to_state.trim()) payload.to_state = measurementForm.to_state.trim();
    try {
      await api.cognitiveFriction.recordMeasurement(payload);
      toast.success('Measurement recorded');
      setMeasurementForm({ agent_id: '', source: 'ANCHORING', resistance_score: '', transition_type: 'CONCEPT_SHIFT', from_state: '', to_state: '' });
      await loadMeasurements();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordTransition = async () => {
    if (!transitionForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: transitionForm.agent_id.trim(),
      transition_type: transitionForm.transition_type,
    };
    if (transitionForm.from_state.trim()) payload.from_state = transitionForm.from_state.trim();
    if (transitionForm.to_state.trim()) payload.to_state = transitionForm.to_state.trim();
    if (transitionForm.friction_score.trim()) payload.friction_score = Number(transitionForm.friction_score);
    if (transitionForm.duration.trim()) payload.duration = Number(transitionForm.duration);
    try {
      await api.cognitiveFriction.recordTransition(payload);
      toast.success('Transition recorded');
      setTransitionForm({ agent_id: '', transition_type: 'CONCEPT_SHIFT', from_state: '', to_state: '', friction_score: '', duration: '' });
      await loadTransitions();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanLubrication = async () => {
    if (!lubricationForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: lubricationForm.agent_id.trim(),
      strategy: lubricationForm.strategy,
    };
    if (lubricationForm.transition_id.trim()) payload.transition_id = lubricationForm.transition_id.trim();
    if (lubricationForm.expected_relief.trim()) payload.expected_relief = Number(lubricationForm.expected_relief);
    try {
      await api.cognitiveFriction.planLubrication(payload);
      toast.success('Lubrication planned');
      setLubricationForm({ agent_id: '', transition_id: '', strategy: 'PRIME', expected_relief: '' });
      await loadLubrications();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAssessRecovery = async () => {
    if (!recoveryForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: recoveryForm.agent_id.trim(),
      from_state: recoveryForm.from_state,
      to_state: recoveryForm.to_state,
      strategy: recoveryForm.strategy,
    };
    if (recoveryForm.transition_id.trim()) payload.transition_id = recoveryForm.transition_id.trim();
    try {
      const result = await api.cognitiveFriction.assessRecovery(payload);
      setRecoveryResult(result);
      toast.success('Recovery assessed');
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
          <h2>🧱 Cognitive Friction</h2>
          <p className="panel-subtitle">Measure transition resistance, plan lubrication, and assess recovery</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive friction...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧱 Cognitive Friction</h2>
        <p className="panel-subtitle">Measure transition resistance, plan lubrication, and assess recovery</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_measurements ?? '-'}</span><span className="stat-label">Measurements</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_transitions ?? '-'}</span><span className="stat-label">Transitions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_lubrications ?? '-'}</span><span className="stat-label">Lubrications</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_recoveries ?? '-'}</span><span className="stat-label">Recoveries</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_resistance ?? '-'}</span><span className="stat-label">Avg Resistance</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'measurement', 'lubrication'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Friction Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Measurements</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_measurements ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Transitions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_transitions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Lubrications</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_lubrications ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Recoveries</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_recoveries ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Resistance</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_resistance ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Measurements</h3>
            <button onClick={() => loadMeasurements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {measurements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No measurements recorded. Record one in the Measurement section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {measurements.slice(0, 10).map((m: any, i: number) => {
                  const id = m.measurement_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>measurement {id} · resistance: {m.resistance_score ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.source && renderBadge(m.source, themeColors.secondary)}
                          {m.regime && renderBadge(m.regime, statusColor(m.regime))}
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

      {/* Measurement Section */}
      {activeSection === 'measurement' && (
        <div className="dashboard-section">
          {/* Record Measurement */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Measurement</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={measurementForm.agent_id} onChange={e => setMeasurementForm({ ...measurementForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Source</label>
                <select value={measurementForm.source} onChange={e => setMeasurementForm({ ...measurementForm, source: e.target.value })}>
                  {FRICTION_SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Resistance Score *</label>
                <input value={measurementForm.resistance_score} onChange={e => setMeasurementForm({ ...measurementForm, resistance_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Transition Type</label>
                <select value={measurementForm.transition_type} onChange={e => setMeasurementForm({ ...measurementForm, transition_type: e.target.value })}>
                  {TRANSITION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>From State</label>
                <input value={measurementForm.from_state} onChange={e => setMeasurementForm({ ...measurementForm, from_state: e.target.value })} placeholder="optional starting state" />
              </div>
              <div className="form-group">
                <label>To State</label>
                <input value={measurementForm.to_state} onChange={e => setMeasurementForm({ ...measurementForm, to_state: e.target.value })} placeholder="optional target state" />
              </div>
            </div>
            <button onClick={handleRecordMeasurement} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Measurement</button>
          </div>

          {/* Record Transition */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Transition</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={transitionForm.agent_id} onChange={e => setTransitionForm({ ...transitionForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Transition Type</label>
                <select value={transitionForm.transition_type} onChange={e => setTransitionForm({ ...transitionForm, transition_type: e.target.value })}>
                  {TRANSITION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>From State</label>
                <input value={transitionForm.from_state} onChange={e => setTransitionForm({ ...transitionForm, from_state: e.target.value })} placeholder="optional starting state" />
              </div>
              <div className="form-group">
                <label>To State</label>
                <input value={transitionForm.to_state} onChange={e => setTransitionForm({ ...transitionForm, to_state: e.target.value })} placeholder="optional target state" />
              </div>
              <div className="form-group">
                <label>Friction Score</label>
                <input value={transitionForm.friction_score} onChange={e => setTransitionForm({ ...transitionForm, friction_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>Duration</label>
                <input value={transitionForm.duration} onChange={e => setTransitionForm({ ...transitionForm, duration: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 12.0" />
              </div>
            </div>
            <button onClick={handleRecordTransition} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Transition</button>
          </div>

          {/* Measurements List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Measurements ({measurements.length})</h3>
            <button onClick={() => loadMeasurements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {measurements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No measurements recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {measurements.slice(0, 30).map((m: any, i: number) => {
                  const id = m.measurement_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'} · resistance: {m.resistance_score ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>measurement {id}{m.transition_type ? ` · ${m.transition_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.source && renderBadge(m.source, themeColors.secondary)}
                          {m.regime && renderBadge(m.regime, statusColor(m.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Transitions List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Transitions ({transitions.length})</h3>
            <button onClick={() => loadTransitions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {transitions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No transitions recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {transitions.slice(0, 30).map((t: any, i: number) => {
                  const id = t.transition_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {t.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>transition {id}{t.from_state ? ` · ${t.from_state}` : ''}{t.to_state ? ` -> ${t.to_state}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {t.transition_type && renderBadge(t.transition_type, themeColors.secondary)}
                          {t.friction_score != null && renderBadge(`friction: ${t.friction_score}`, themeColors.primary)}
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

      {/* Lubrication Section */}
      {activeSection === 'lubrication' && (
        <div className="dashboard-section">
          {/* Plan Lubrication */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Lubrication</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={lubricationForm.agent_id} onChange={e => setLubricationForm({ ...lubricationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Transition ID</label>
                <input value={lubricationForm.transition_id} onChange={e => setLubricationForm({ ...lubricationForm, transition_id: e.target.value })} placeholder="optional transition id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={lubricationForm.strategy} onChange={e => setLubricationForm({ ...lubricationForm, strategy: e.target.value })}>
                  {LUBRICATION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Relief</label>
                <input value={lubricationForm.expected_relief} onChange={e => setLubricationForm({ ...lubricationForm, expected_relief: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
            </div>
            <button onClick={handlePlanLubrication} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Lubrication</button>
          </div>

          {/* Assess Recovery */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Assess Recovery</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={recoveryForm.agent_id} onChange={e => setRecoveryForm({ ...recoveryForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Transition ID</label>
                <input value={recoveryForm.transition_id} onChange={e => setRecoveryForm({ ...recoveryForm, transition_id: e.target.value })} placeholder="optional transition id" />
              </div>
              <div className="form-group">
                <label>From State</label>
                <select value={recoveryForm.from_state} onChange={e => setRecoveryForm({ ...recoveryForm, from_state: e.target.value })}>
                  {RECOVERY_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To State</label>
                <select value={recoveryForm.to_state} onChange={e => setRecoveryForm({ ...recoveryForm, to_state: e.target.value })}>
                  {RECOVERY_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={recoveryForm.strategy} onChange={e => setRecoveryForm({ ...recoveryForm, strategy: e.target.value })}>
                  {LUBRICATION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleAssessRecovery} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Assess Recovery</button>
            {recoveryResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(recoveryResult, null, 2)}</pre>
            )}
          </div>

          {/* Lubrications List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Lubrications ({lubrications.length})</h3>
            <button onClick={() => loadLubrications()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {lubrications.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No lubrications planned. Plan one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {lubrications.slice(0, 30).map((l: any, i: number) => {
                  const id = l.lubrication_id ?? l.plan_id ?? l.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {l.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>lubrication {id}{l.transition_id ? ` · transition: ${l.transition_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {l.strategy && renderBadge(l.strategy, themeColors.secondary)}
                          {l.expected_relief != null && renderBadge(`relief: ${l.expected_relief}`, themeColors.primary)}
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

export default CognitiveFrictionPanel;
