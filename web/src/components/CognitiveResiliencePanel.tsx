import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: green for cognitive resilience
const themeColors = {
  primary: '#059669',
  secondary: '#10b981',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

// Enum values must match backend CapacityType / RecoveryState / ResilienceRegime / AdaptationStrategy / StressSignature exactly (uppercase).
const CAPACITY_TYPES = ['EMOTIONAL', 'EPISTEMIC', 'PROCEDURAL', 'CONTEXTUAL', 'STRUCTURAL', 'RELATIONAL'];
const RECOVERY_STATES = ['BROKEN', 'STRESSED', 'STRAINED', 'RECOVERING', 'STABLE', 'FLOURISHING'];
const ADAPTATION_STRATEGIES = ['HOLD', 'COMPENSATE', 'RESTRUCTURE', 'REGENERATE', 'EXTEND', 'HARDEN'];
const STRESS_SIGNATURES = ['IMPULSE', 'SPIKE', 'PLATEAU', 'OSCILLATION', 'CASCADE', 'BASELINE_DRIFT'];

// Map a recovery state value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  BROKEN: '#7f1d1d',
  STRESSED: '#dc2626',
  STRAINED: '#f59e0b',
  RECOVERING: '#0ea5e9',
  STABLE: '#10b981',
  FLOURISHING: '#16a34a',
};

export const CognitiveResiliencePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'readings' | 'events' | 'snapshots' | 'plans' | 'recoveries'>('overview');

  // Readings / events / snapshots / plans / recoveries
  const [readings, setReadings] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [recoveries, setRecoveries] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    capacity_type: 'EMOTIONAL',
    capacity_score: '',
    recovery_rate: '',
    recovery_state: 'STABLE',
    intensity: '',
    notes: '',
  });

  // Record event form
  const [eventForm, setEventForm] = useState({
    agent_id: '',
    source: '',
    magnitude: '',
    signature: 'IMPULSE',
    duration_ms: '',
    notes: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan adaptation form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'HOLD',
    target_capacity: '',
    rationale: '',
  });

  // Record recovery form
  const [recoveryForm, setRecoveryForm] = useState({
    agent_id: '',
    from_state: 'STRESSED',
    to_state: 'STABLE',
    recovery_ms: '',
    residual_stress: '',
    notes: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveResilience.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive resilience stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveResilience.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadEvents = async () => {
    try {
      const result = await api.cognitiveResilience.listEvents();
      const list = Array.isArray(result) ? result : (result?.events ?? []);
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  };

  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveResilience.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveResilience.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  const loadRecoveries = async () => {
    try {
      const result = await api.cognitiveResilience.listRecoveries();
      const list = Array.isArray(result) ? result : (result?.recoveries ?? []);
      setRecoveries(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load recoveries');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadEvents();
      loadSnapshots();
      loadPlans();
      loadRecoveries();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      capacity_type: readingForm.capacity_type,
      capacity_score: readingForm.capacity_score.trim() === '' ? 0.5 : Number(readingForm.capacity_score),
      recovery_rate: readingForm.recovery_rate.trim() === '' ? 0 : Number(readingForm.recovery_rate),
      recovery_state: readingForm.recovery_state,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveResilience.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', capacity_type: 'EMOTIONAL', capacity_score: '', recovery_rate: '', recovery_state: 'STABLE', intensity: '', notes: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordEvent = async () => {
    if (!eventForm.agent_id.trim() || !eventForm.source.trim()) {
      toast.error('Agent ID and source are required');
      return;
    }
    const payload: any = {
      agent_id: eventForm.agent_id.trim(),
      source: eventForm.source.trim(),
      magnitude: eventForm.magnitude.trim() === '' ? 0 : Number(eventForm.magnitude),
      signature: eventForm.signature,
      duration_ms: eventForm.duration_ms.trim() === '' ? 0 : Number(eventForm.duration_ms),
    };
    if (eventForm.notes) payload.notes = eventForm.notes.trim();
    try {
      await api.cognitiveResilience.recordEvent(payload);
      toast.success('Event recorded');
      setEventForm({ agent_id: '', source: '', magnitude: '', signature: 'IMPULSE', duration_ms: '', notes: '' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      const result = await api.cognitiveResilience.takeSnapshot({ agent_id: snapshotForm.agent_id.trim() });
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanAdaptation = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_capacity: planForm.target_capacity.trim() === '' ? 0 : Number(planForm.target_capacity),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveResilience.planAdaptation(payload);
      toast.success('Adaptation plan created');
      setPlanForm({ agent_id: '', strategy: 'HOLD', target_capacity: '', rationale: '' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordRecovery = async () => {
    if (!recoveryForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: recoveryForm.agent_id.trim(),
      from_state: recoveryForm.from_state,
      to_state: recoveryForm.to_state,
      recovery_ms: recoveryForm.recovery_ms.trim() === '' ? 0 : Number(recoveryForm.recovery_ms),
      residual_stress: recoveryForm.residual_stress.trim() === '' ? 0 : Number(recoveryForm.residual_stress),
    };
    if (recoveryForm.notes) payload.notes = recoveryForm.notes.trim();
    try {
      await api.cognitiveResilience.recordRecovery(payload);
      toast.success('Recovery recorded');
      setRecoveryForm({ agent_id: '', from_state: 'STRESSED', to_state: 'STABLE', recovery_ms: '', residual_stress: '', notes: '' });
      await loadRecoveries();
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
          <h2>🛡️ Cognitive Resilience</h2>
          <p className="panel-subtitle">Measure capacities, record stress events, and track recovery across the cognitive resilience system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive resilience...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🛡️ Cognitive Resilience</h2>
        <p className="panel-subtitle">Measure capacities, record stress events, and track recovery across the cognitive resilience system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_capacity ?? '-'}</span><span className="stat-label">Avg Capacity</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'events', 'snapshots', 'plans', 'recoveries'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Resilience Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_events ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Capacity</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_capacity ?? 0}</div>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.capacity_type ? ` · ${r.capacity_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.capacity_type && renderBadge(r.capacity_type, themeColors.secondary)}
                          {r.recovery_state && renderBadge(r.recovery_state, statusColor(r.recovery_state))}
                          {typeof r.capacity_score !== 'undefined' && renderBadge(`cap ${r.capacity_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Events</h3>
            <button onClick={() => loadEvents()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {events.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No events recorded. Record one in the Events section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {events.slice(0, 10).map((e: any, i: number) => {
                  const id = e.event_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>event {id}{e.source ? ` · ${e.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.signature && renderBadge(e.signature, themeColors.secondary)}
                          {typeof e.magnitude !== 'undefined' && renderBadge(`mag ${e.magnitude}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Recoveries</h3>
            <button onClick={() => loadRecoveries()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {recoveries.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No recoveries recorded. Record one in the Recoveries section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {recoveries.slice(0, 10).map((r: any, i: number) => {
                  const id = r.recovery_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>recovery {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.from_state && r.to_state && renderBadge(`${r.from_state}->${r.to_state}`, statusColor(r.to_state))}
                          {typeof r.recovery_ms !== 'undefined' && renderBadge(`${r.recovery_ms}ms`, themeColors.primary)}
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

      {/* Readings Section */}
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
                <label>Capacity Type</label>
                <select className="form-select" value={readingForm.capacity_type} onChange={e => setReadingForm({ ...readingForm, capacity_type: e.target.value })}>
                  {CAPACITY_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Recovery State</label>
                <select className="form-select" value={readingForm.recovery_state} onChange={e => setReadingForm({ ...readingForm, recovery_state: e.target.value })}>
                  {RECOVERY_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Capacity Score</label>
                <input className="form-input" value={readingForm.capacity_score} onChange={e => setReadingForm({ ...readingForm, capacity_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group">
                <label>Recovery Rate</label>
                <input className="form-input" value={readingForm.recovery_rate} onChange={e => setReadingForm({ ...readingForm, recovery_rate: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.4" />
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.capacity_type ? ` · ${r.capacity_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.capacity_type && renderBadge(r.capacity_type, themeColors.secondary)}
                          {r.recovery_state && renderBadge(r.recovery_state, statusColor(r.recovery_state))}
                          {typeof r.capacity_score !== 'undefined' && renderBadge(`cap ${r.capacity_score}`, themeColors.primary)}
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

      {/* Events Section */}
      {activeSection === 'events' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Event</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={eventForm.agent_id} onChange={e => setEventForm({ ...eventForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Source *</label>
                <input className="form-input" value={eventForm.source} onChange={e => setEventForm({ ...eventForm, source: e.target.value })} placeholder="stress source" />
              </div>
              <div className="form-group">
                <label>Signature</label>
                <select className="form-select" value={eventForm.signature} onChange={e => setEventForm({ ...eventForm, signature: e.target.value })}>
                  {STRESS_SIGNATURES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Magnitude</label>
                <input className="form-input" value={eventForm.magnitude} onChange={e => setEventForm({ ...eventForm, magnitude: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Duration (ms)</label>
                <input className="form-input" value={eventForm.duration_ms} onChange={e => setEventForm({ ...eventForm, duration_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 1000" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={eventForm.notes} onChange={e => setEventForm({ ...eventForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Event</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Events ({events.length})</h3>
            <button onClick={() => loadEvents()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {events.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No events recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {events.slice(0, 30).map((e: any, i: number) => {
                  const id = e.event_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>event {id}{e.source ? ` · ${e.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.signature && renderBadge(e.signature, themeColors.secondary)}
                          {typeof e.magnitude !== 'undefined' && renderBadge(`mag ${e.magnitude}`, themeColors.primary)}
                          {typeof e.duration_ms !== 'undefined' && renderBadge(`${e.duration_ms}ms`, themeColors.secondary)}
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

      {/* Snapshots Section */}
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
                          {s.regime && renderBadge(s.regime, statusColor(s.regime))}
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

      {/* Plans Section */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Adaptation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {ADAPTATION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Capacity</label>
                <input className="form-input" value={planForm.target_capacity} onChange={e => setPlanForm({ ...planForm, target_capacity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for plan" />
              </div>
            </div>
            <button onClick={handlePlanAdaptation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Adaptation</button>
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
                          {typeof p.target_capacity !== 'undefined' && renderBadge(`cap ${p.target_capacity}`, themeColors.primary)}
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

      {/* Recoveries Section */}
      {activeSection === 'recoveries' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Recovery</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={recoveryForm.agent_id} onChange={e => setRecoveryForm({ ...recoveryForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>From State</label>
                <select className="form-select" value={recoveryForm.from_state} onChange={e => setRecoveryForm({ ...recoveryForm, from_state: e.target.value })}>
                  {RECOVERY_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To State</label>
                <select className="form-select" value={recoveryForm.to_state} onChange={e => setRecoveryForm({ ...recoveryForm, to_state: e.target.value })}>
                  {RECOVERY_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Recovery (ms)</label>
                <input className="form-input" value={recoveryForm.recovery_ms} onChange={e => setRecoveryForm({ ...recoveryForm, recovery_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 2000" />
              </div>
              <div className="form-group">
                <label>Residual Stress</label>
                <input className="form-input" value={recoveryForm.residual_stress} onChange={e => setRecoveryForm({ ...recoveryForm, residual_stress: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.2" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={recoveryForm.notes} onChange={e => setRecoveryForm({ ...recoveryForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordRecovery} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Recovery</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recoveries ({recoveries.length})</h3>
            <button onClick={() => loadRecoveries()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {recoveries.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No recoveries recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {recoveries.slice(0, 30).map((r: any, i: number) => {
                  const id = r.recovery_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>recovery {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.from_state && r.to_state && renderBadge(`${r.from_state}->${r.to_state}`, statusColor(r.to_state))}
                          {typeof r.recovery_ms !== 'undefined' && renderBadge(`${r.recovery_ms}ms`, themeColors.primary)}
                          {typeof r.residual_stress !== 'undefined' && renderBadge(`stress ${r.residual_stress}`, themeColors.secondary)}
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

export default CognitiveResiliencePanel;
