import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: indigo for cognitive singularity
const themeColors = {
  primary: '#6366f1',
  secondary: '#818cf8',
  bg: '#eef2ff',
  border: '#c7d2fe',
  accent: '#e0e7ff',
  text: '#312e81',
};

// Enum values must match backend FocusTarget / FocusSignature / SingularityRegime / DeepeningStrategy / FocusTrigger exactly (uppercase).
const FOCUS_TARGETS = ['PROBLEM', 'INSIGHT', 'DECISION', 'CREATION', 'MEMORY', 'VALUE'];
const FOCUS_SIGNATURES = ['GRADUAL', 'ABRUPT', 'CYCLING', 'WAVE', 'SPIRALING', 'INSTANT'];
const DEEPENING_STRATEGIES = ['HOLD', 'EXPAND', 'NARROW', 'DISSOLVE', 'INTEGRATE', 'RELEASE'];
const FOCUS_TRIGGERS = ['QUESTION', 'EVIDENCE', 'INTUITION', 'EMOTION', 'NOVELTY', 'CONTRADICTION'];

// Map a focus signature value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  GRADUAL: '#0ea5e9',
  ABRUPT: '#dc2626',
  CYCLING: '#a855f7',
  WAVE: '#06b6d4',
  SPIRALING: '#f59e0b',
  INSTANT: '#16a34a',
};

export const CognitiveSingularityPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'readings' | 'events' | 'snapshots' | 'plans' | 'focuses'>('overview');

  // Readings / events / snapshots / plans / focuses
  const [readings, setReadings] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [focuses, setFocuses] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    focus_target: 'PROBLEM',
    focus_score: '',
    convergence: '',
    focus_signature: 'GRADUAL',
    intensity: '',
    notes: '',
  });

  // Record event form
  const [eventForm, setEventForm] = useState({
    agent_id: '',
    target: '',
    depth_score: '',
    duration_ms: '',
    trigger: 'QUESTION',
    notes: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan deepening form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'HOLD',
    target_focus: '',
    rationale: '',
  });

  // Record focus form
  const [focusForm, setFocusForm] = useState({
    agent_id: '',
    from_state: 'GRADUAL',
    to_state: 'GRADUAL',
    depth_delta: '',
    focus_signature: 'GRADUAL',
    notes: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveSingularity.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive singularity stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveSingularity.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadEvents = async () => {
    try {
      const result = await api.cognitiveSingularity.listEvents();
      const list = Array.isArray(result) ? result : (result?.events ?? []);
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  };

  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveSingularity.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveSingularity.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  const loadFocuses = async () => {
    try {
      const result = await api.cognitiveSingularity.listFocuses();
      const list = Array.isArray(result) ? result : (result?.focuses ?? []);
      setFocuses(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load focuses');
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
      loadFocuses();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      focus_target: readingForm.focus_target,
      focus_score: readingForm.focus_score.trim() === '' ? 0.5 : Number(readingForm.focus_score),
      convergence: readingForm.convergence.trim() === '' ? 0 : Number(readingForm.convergence),
      focus_signature: readingForm.focus_signature,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveSingularity.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', focus_target: 'PROBLEM', focus_score: '', convergence: '', focus_signature: 'GRADUAL', intensity: '', notes: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordEvent = async () => {
    if (!eventForm.agent_id.trim() || !eventForm.target.trim()) {
      toast.error('Agent ID and target are required');
      return;
    }
    const payload: any = {
      agent_id: eventForm.agent_id.trim(),
      target: eventForm.target.trim(),
      depth_score: eventForm.depth_score.trim() === '' ? 0 : Number(eventForm.depth_score),
      duration_ms: eventForm.duration_ms.trim() === '' ? 0 : Number(eventForm.duration_ms),
      trigger: eventForm.trigger,
    };
    if (eventForm.notes) payload.notes = eventForm.notes.trim();
    try {
      await api.cognitiveSingularity.recordEvent(payload);
      toast.success('Event recorded');
      setEventForm({ agent_id: '', target: '', depth_score: '', duration_ms: '', trigger: 'QUESTION', notes: '' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      const result = await api.cognitiveSingularity.takeSnapshot({ agent_id: snapshotForm.agent_id.trim() });
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanDeepening = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_focus: planForm.target_focus.trim() === '' ? 0 : Number(planForm.target_focus),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveSingularity.planDeepening(payload);
      toast.success('Deepening plan created');
      setPlanForm({ agent_id: '', strategy: 'HOLD', target_focus: '', rationale: '' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordFocus = async () => {
    if (!focusForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: focusForm.agent_id.trim(),
      from_state: focusForm.from_state,
      to_state: focusForm.to_state,
      depth_delta: focusForm.depth_delta.trim() === '' ? 0 : Number(focusForm.depth_delta),
      focus_signature: focusForm.focus_signature,
    };
    if (focusForm.notes) payload.notes = focusForm.notes.trim();
    try {
      await api.cognitiveSingularity.recordFocus(payload);
      toast.success('Focus recorded');
      setFocusForm({ agent_id: '', from_state: 'GRADUAL', to_state: 'GRADUAL', depth_delta: '', focus_signature: 'GRADUAL', notes: '' });
      await loadFocuses();
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
          <h2>✨ Cognitive Singularity</h2>
          <p className="panel-subtitle">Track deep focus, plan convergence, and record singular insights across the cognitive singularity system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive singularity...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>✨ Cognitive Singularity</h2>
        <p className="panel-subtitle">Track deep focus, plan convergence, and record singular insights across the cognitive singularity system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_focus ?? '-'}</span><span className="stat-label">Avg Focus</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'events', 'snapshots', 'plans', 'focuses'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Singularity Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Focus</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_focus ?? 0}</div>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.focus_target ? ` · ${r.focus_target}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.focus_target && renderBadge(r.focus_target, themeColors.secondary)}
                          {r.focus_signature && renderBadge(r.focus_signature, statusColor(r.focus_signature))}
                          {typeof r.focus_score !== 'undefined' && renderBadge(`focus ${r.focus_score}`, themeColors.primary)}
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>event {id}{e.target ? ` · ${e.target}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.trigger && renderBadge(e.trigger, themeColors.secondary)}
                          {typeof e.depth_score !== 'undefined' && renderBadge(`depth ${e.depth_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Focuses</h3>
            <button onClick={() => loadFocuses()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {focuses.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No focuses recorded. Record one in the Focuses section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {focuses.slice(0, 10).map((f: any, i: number) => {
                  const id = f.focus_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>focus {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.from_state && f.to_state && renderBadge(`${f.from_state}->${f.to_state}`, themeColors.secondary)}
                          {f.focus_signature && renderBadge(f.focus_signature, statusColor(f.focus_signature))}
                          {typeof f.depth_delta !== 'undefined' && renderBadge(`delta ${f.depth_delta}`, themeColors.primary)}
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
                <label>Focus Target</label>
                <select className="form-select" value={readingForm.focus_target} onChange={e => setReadingForm({ ...readingForm, focus_target: e.target.value })}>
                  {FOCUS_TARGETS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Focus Signature</label>
                <select className="form-select" value={readingForm.focus_signature} onChange={e => setReadingForm({ ...readingForm, focus_signature: e.target.value })}>
                  {FOCUS_SIGNATURES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Focus Score</label>
                <input className="form-input" value={readingForm.focus_score} onChange={e => setReadingForm({ ...readingForm, focus_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group">
                <label>Convergence</label>
                <input className="form-input" value={readingForm.convergence} onChange={e => setReadingForm({ ...readingForm, convergence: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.focus_target ? ` · ${r.focus_target}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.focus_target && renderBadge(r.focus_target, themeColors.secondary)}
                          {r.focus_signature && renderBadge(r.focus_signature, statusColor(r.focus_signature))}
                          {typeof r.focus_score !== 'undefined' && renderBadge(`focus ${r.focus_score}`, themeColors.primary)}
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
                <label>Target *</label>
                <input className="form-input" value={eventForm.target} onChange={e => setEventForm({ ...eventForm, target: e.target.value })} placeholder="event target" />
              </div>
              <div className="form-group">
                <label>Trigger</label>
                <select className="form-select" value={eventForm.trigger} onChange={e => setEventForm({ ...eventForm, trigger: e.target.value })}>
                  {FOCUS_TRIGGERS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Depth Score</label>
                <input className="form-input" value={eventForm.depth_score} onChange={e => setEventForm({ ...eventForm, depth_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group">
                <label>Duration (ms)</label>
                <input className="form-input" value={eventForm.duration_ms} onChange={e => setEventForm({ ...eventForm, duration_ms: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 1500" />
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>event {id}{e.target ? ` · ${e.target}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.trigger && renderBadge(e.trigger, themeColors.secondary)}
                          {typeof e.depth_score !== 'undefined' && renderBadge(`depth ${e.depth_score}`, themeColors.primary)}
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
            <h3 style={{ color: themeColors.text }}>Plan Deepening</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {DEEPENING_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Focus</label>
                <input className="form-input" value={planForm.target_focus} onChange={e => setPlanForm({ ...planForm, target_focus: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for plan" />
              </div>
            </div>
            <button onClick={handlePlanDeepening} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Deepening</button>
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
                          {typeof p.target_focus !== 'undefined' && renderBadge(`focus ${p.target_focus}`, themeColors.primary)}
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

      {/* Focuses Section */}
      {activeSection === 'focuses' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Focus</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={focusForm.agent_id} onChange={e => setFocusForm({ ...focusForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>From State</label>
                <select className="form-select" value={focusForm.from_state} onChange={e => setFocusForm({ ...focusForm, from_state: e.target.value })}>
                  {FOCUS_SIGNATURES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To State</label>
                <select className="form-select" value={focusForm.to_state} onChange={e => setFocusForm({ ...focusForm, to_state: e.target.value })}>
                  {FOCUS_SIGNATURES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Focus Signature</label>
                <select className="form-select" value={focusForm.focus_signature} onChange={e => setFocusForm({ ...focusForm, focus_signature: e.target.value })}>
                  {FOCUS_SIGNATURES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Depth Delta</label>
                <input className="form-input" value={focusForm.depth_delta} onChange={e => setFocusForm({ ...focusForm, depth_delta: e.target.value })} type="number" min="-1" max="1" step="0.01" placeholder="e.g. 0.2" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={focusForm.notes} onChange={e => setFocusForm({ ...focusForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordFocus} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Focus</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Focuses ({focuses.length})</h3>
            <button onClick={() => loadFocuses()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {focuses.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No focuses recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {focuses.slice(0, 30).map((f: any, i: number) => {
                  const id = f.focus_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>focus {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.from_state && f.to_state && renderBadge(`${f.from_state}->${f.to_state}`, themeColors.secondary)}
                          {f.focus_signature && renderBadge(f.focus_signature, statusColor(f.focus_signature))}
                          {typeof f.depth_delta !== 'undefined' && renderBadge(`delta ${f.depth_delta}`, themeColors.primary)}
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

export default CognitiveSingularityPanel;
