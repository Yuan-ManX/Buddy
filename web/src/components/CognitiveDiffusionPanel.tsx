import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: fuchsia for cognitive diffusion
const themeColors = {
  primary: '#c026d3',
  secondary: '#d946ef',
  bg: '#fdf4ff',
  border: '#f5d0fe',
  accent: '#fae8ff',
  text: '#701a75',
};

// Enum values must match backend DiffusionMedia / DiffusionRegime / GradientDirection / DiffusionBarrier / EqualizationStrategy exactly (uppercase).
const DIFFUSION_MEDIA = ['BELIEF_NETWORK', 'CONCEPT_GRAPH', 'MEMORY_FIELD', 'ATTENTION_FIELD', 'EMOTIONAL_FIELD'];
const DIFFUSION_REGIMES = ['STAGNANT', 'SLOW', 'STEADY', 'RAPID', 'SATURATED', 'OSCILLATORY'];
const GRADIENT_DIRECTIONS = ['EXPANDING', 'CONTRACTING', 'STABLE', 'REVERSING', 'PULSING'];
const DIFFUSION_BARRIERS = ['NONE', 'PARTIAL', 'SELECTIVE', 'STRONG', 'IMPERMEABLE'];
const EQUALIZATION_STRATEGIES = ['ACCELERATE', 'DAMPEN', 'CHANNEL', 'INSULATE', 'SEED', 'DRAIN'];

// Map a diffusion regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  STAGNANT: '#dc2626',
  SLOW: '#f97316',
  STEADY: '#0ea5e9',
  RAPID: '#16a34a',
  SATURATED: '#7c3aed',
  OSCILLATORY: '#0891b2',
};

export const CognitiveDiffusionPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reading' | 'plan'>('overview');

  // Readings / events / plans
  const [readings, setReadings] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [gradientResult, setGradientResult] = useState<any>(null);

  // Read concentration form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    media: 'BELIEF_NETWORK',
    concentration: '',
    regime: 'STEADY',
  });

  // Record event form
  const [eventForm, setEventForm] = useState({
    agent_id: '',
    media: 'BELIEF_NETWORK',
    direction: 'EXPANDING',
    magnitude: '',
  });

  // Plan equalization form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    reading_id: '',
    strategy: 'ACCELERATE',
    barrier: 'NONE',
  });

  // Record gradient form
  const [gradientForm, setGradientForm] = useState({
    agent_id: '',
    direction: 'EXPANDING',
    barrier: 'NONE',
    slope: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveDiffusion.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive diffusion stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveDiffusion.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadEvents = async () => {
    try {
      const result = await api.cognitiveDiffusion.listEvents();
      const list = Array.isArray(result) ? result : (result?.events ?? []);
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveDiffusion.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
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
      loadPlans();
    }
  }, [activeSection]);

  const handleReadConcentration = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      media: readingForm.media,
      regime: readingForm.regime,
    };
    if (readingForm.concentration.trim()) payload.concentration = Number(readingForm.concentration);
    try {
      await api.cognitiveDiffusion.readConcentration(payload);
      toast.success('Concentration read');
      setReadingForm({ agent_id: '', media: 'BELIEF_NETWORK', concentration: '', regime: 'STEADY' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordEvent = async () => {
    if (!eventForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: eventForm.agent_id.trim(),
      media: eventForm.media,
      direction: eventForm.direction,
    };
    if (eventForm.magnitude.trim()) payload.magnitude = Number(eventForm.magnitude);
    try {
      await api.cognitiveDiffusion.recordEvent(payload);
      toast.success('Event recorded');
      setEventForm({ agent_id: '', media: 'BELIEF_NETWORK', direction: 'EXPANDING', magnitude: '' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanEqualization = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      barrier: planForm.barrier,
    };
    if (planForm.reading_id.trim()) payload.reading_id = planForm.reading_id.trim();
    try {
      await api.cognitiveDiffusion.planEqualization(payload);
      toast.success('Equalization planned');
      setPlanForm({ agent_id: '', reading_id: '', strategy: 'ACCELERATE', barrier: 'NONE' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordGradient = async () => {
    if (!gradientForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: gradientForm.agent_id.trim(),
      direction: gradientForm.direction,
      barrier: gradientForm.barrier,
    };
    if (gradientForm.slope.trim()) payload.slope = Number(gradientForm.slope);
    try {
      const result = await api.cognitiveDiffusion.recordGradient(payload);
      setGradientResult(result);
      toast.success('Gradient recorded');
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
          <h2>🌊 Cognitive Diffusion</h2>
          <p className="panel-subtitle">Read concentrations, record diffusion events, and plan equalization across fields</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive diffusion...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌊 Cognitive Diffusion</h2>
        <p className="panel-subtitle">Read concentrations, record diffusion events, and plan equalization across fields</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_plans ?? '-'}</span><span className="stat-label">Plans</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_gradients ?? '-'}</span><span className="stat-label">Gradients</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_concentration ?? '-'}</span><span className="stat-label">Avg Concentration</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reading', 'plan'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Diffusion Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Plans</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_plans ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Gradients</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_gradients ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Concentration</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_concentration ?? 0}</div>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.concentration != null ? ` · concentration: ${r.concentration}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.media && renderBadge(r.media, themeColors.secondary)}
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

      {/* Reading Section */}
      {activeSection === 'reading' && (
        <div className="dashboard-section">
          {/* Read Concentration */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Read Concentration</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Media</label>
                <select value={readingForm.media} onChange={e => setReadingForm({ ...readingForm, media: e.target.value })}>
                  {DIFFUSION_MEDIA.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Concentration</label>
                <input value={readingForm.concentration} onChange={e => setReadingForm({ ...readingForm, concentration: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Regime</label>
                <select value={readingForm.regime} onChange={e => setReadingForm({ ...readingForm, regime: e.target.value })}>
                  {DIFFUSION_REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleReadConcentration} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Read Concentration</button>
          </div>

          {/* Record Event */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Event</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={eventForm.agent_id} onChange={e => setEventForm({ ...eventForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Media</label>
                <select value={eventForm.media} onChange={e => setEventForm({ ...eventForm, media: e.target.value })}>
                  {DIFFUSION_MEDIA.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Direction</label>
                <select value={eventForm.direction} onChange={e => setEventForm({ ...eventForm, direction: e.target.value })}>
                  {GRADIENT_DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Magnitude</label>
                <input value={eventForm.magnitude} onChange={e => setEventForm({ ...eventForm, magnitude: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.4" />
              </div>
            </div>
            <button onClick={handleRecordEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Event</button>
          </div>

          {/* Readings List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.concentration != null ? ` · concentration: ${r.concentration}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.media && renderBadge(r.media, themeColors.secondary)}
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Events List */}
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>event {id}{e.magnitude != null ? ` · magnitude: ${e.magnitude}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.media && renderBadge(e.media, themeColors.secondary)}
                          {e.direction && renderBadge(e.direction, themeColors.primary)}
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
          {/* Plan Equalization */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Equalization</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Reading ID</label>
                <input value={planForm.reading_id} onChange={e => setPlanForm({ ...planForm, reading_id: e.target.value })} placeholder="optional reading id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {EQUALIZATION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Barrier</label>
                <select value={planForm.barrier} onChange={e => setPlanForm({ ...planForm, barrier: e.target.value })}>
                  {DIFFUSION_BARRIERS.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handlePlanEqualization} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Equalization</button>
          </div>

          {/* Record Gradient */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Gradient</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={gradientForm.agent_id} onChange={e => setGradientForm({ ...gradientForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Direction</label>
                <select value={gradientForm.direction} onChange={e => setGradientForm({ ...gradientForm, direction: e.target.value })}>
                  {GRADIENT_DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Barrier</label>
                <select value={gradientForm.barrier} onChange={e => setGradientForm({ ...gradientForm, barrier: e.target.value })}>
                  {DIFFUSION_BARRIERS.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Slope</label>
                <input value={gradientForm.slope} onChange={e => setGradientForm({ ...gradientForm, slope: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.5" />
              </div>
            </div>
            <button onClick={handleRecordGradient} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Gradient</button>
            {gradientResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(gradientResult, null, 2)}</pre>
            )}
          </div>

          {/* Plans List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Plans ({plans.length})</h3>
            <button onClick={() => loadPlans()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {plans.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No plans recorded. Plan one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {plans.slice(0, 30).map((p: any, i: number) => {
                  const id = p.plan_id ?? p.equalization_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>plan {id}{p.reading_id ? ` · reading: ${p.reading_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.strategy && renderBadge(p.strategy, themeColors.secondary)}
                          {p.barrier && renderBadge(p.barrier, themeColors.primary)}
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

export default CognitiveDiffusionPanel;
