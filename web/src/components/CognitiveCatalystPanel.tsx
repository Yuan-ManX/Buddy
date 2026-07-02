import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: lime for cognitive catalyst
const themeColors = {
  primary: '#65a30d',
  secondary: '#84cc16',
  bg: '#f7fee7',
  border: '#d9f99d',
  accent: '#ecfccb',
  text: '#365314',
};

// Enum values must match backend CatalystType / CatalysisOutcome / ActivationState / SelectivityLevel / CatalysisRegime exactly (uppercase).
const CATALYST_TYPES = ['CONTEXTUAL', 'CONCEPTUAL', 'FRAMING', 'EMOTIONAL', 'SOCIAL', 'ENVIRONMENTAL'];
const CATALYSIS_OUTCOMES = ['ACCELERATED', 'FACILITATED', 'NEUTRAL', 'INHIBITED', 'BLOCKED'];
const ACTIVATION_STATES = ['DORMANT', 'PRIMED', 'ACTIVE', 'SPENT', 'DEACTIVATED'];
const SELECTIVITY_LEVELS = ['BROAD', 'MODERATE', 'SPECIFIC', 'ULTRA_SPECIFIC'];
const CATALYSIS_REGIMES = ['INERT', 'SPORADIC', 'MODERATE', 'ACTIVE', 'PROLIFIC'];

// Map a catalysis regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  INERT: '#9ca3af',
  SPORADIC: '#f97316',
  MODERATE: '#0ea5e9',
  ACTIVE: '#65a30d',
  PROLIFIC: '#16a34a',
};

export const CognitiveCatalystPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'catalyst' | 'plan'>('overview');

  // Catalysts / events / plans
  const [catalysts, setCatalysts] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [decayResult, setDecayResult] = useState<any>(null);

  // Register catalyst form
  const [catalystForm, setCatalystForm] = useState({
    agent_id: '',
    name: '',
    catalyst_type: 'CONTEXTUAL',
    selectivity: 'MODERATE',
  });

  // Record event form
  const [eventForm, setEventForm] = useState({
    agent_id: '',
    catalyst_id: '',
    outcome: 'NEUTRAL',
    activation: 'DORMANT',
  });

  // Plan activation form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    catalyst_id: '',
    target_state: 'PRIMED',
    selectivity: 'MODERATE',
  });

  // Record decay form
  const [decayForm, setDecayForm] = useState({
    agent_id: '',
    catalyst_id: '',
    regime: 'INERT',
    decay_rate: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveCatalyst.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive catalyst stats');
    } finally {
      setLoading(false);
    }
  };

  const loadCatalysts = async () => {
    try {
      const result = await api.cognitiveCatalyst.listCatalysts();
      const list = Array.isArray(result) ? result : (result?.catalysts ?? []);
      setCatalysts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load catalysts');
    }
  };

  const loadEvents = async () => {
    try {
      const result = await api.cognitiveCatalyst.listEvents();
      const list = Array.isArray(result) ? result : (result?.events ?? []);
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveCatalyst.listPlans();
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
      loadCatalysts();
      loadEvents();
      loadPlans();
    }
  }, [activeSection]);

  const handleRegisterCatalyst = async () => {
    if (!catalystForm.agent_id.trim() || !catalystForm.name.trim()) {
      toast.error('Agent ID and name are required');
      return;
    }
    const payload: any = {
      agent_id: catalystForm.agent_id.trim(),
      name: catalystForm.name.trim(),
      catalyst_type: catalystForm.catalyst_type,
      selectivity: catalystForm.selectivity,
    };
    try {
      await api.cognitiveCatalyst.registerCatalyst(payload);
      toast.success('Catalyst registered');
      setCatalystForm({ agent_id: '', name: '', catalyst_type: 'CONTEXTUAL', selectivity: 'MODERATE' });
      await loadCatalysts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordEvent = async () => {
    if (!eventForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: eventForm.agent_id.trim(),
      outcome: eventForm.outcome,
      activation: eventForm.activation,
    };
    if (eventForm.catalyst_id.trim()) payload.catalyst_id = eventForm.catalyst_id.trim();
    try {
      await api.cognitiveCatalyst.recordEvent(payload);
      toast.success('Event recorded');
      setEventForm({ agent_id: '', catalyst_id: '', outcome: 'NEUTRAL', activation: 'DORMANT' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanActivation = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      target_state: planForm.target_state,
      selectivity: planForm.selectivity,
    };
    if (planForm.catalyst_id.trim()) payload.catalyst_id = planForm.catalyst_id.trim();
    try {
      await api.cognitiveCatalyst.planActivation(payload);
      toast.success('Activation planned');
      setPlanForm({ agent_id: '', catalyst_id: '', target_state: 'PRIMED', selectivity: 'MODERATE' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordDecay = async () => {
    if (!decayForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: decayForm.agent_id.trim(),
      regime: decayForm.regime,
    };
    if (decayForm.catalyst_id.trim()) payload.catalyst_id = decayForm.catalyst_id.trim();
    if (decayForm.decay_rate.trim()) payload.decay_rate = Number(decayForm.decay_rate);
    try {
      const result = await api.cognitiveCatalyst.recordDecay(payload);
      setDecayResult(result);
      toast.success('Decay recorded');
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
          <h2>⚗️ Cognitive Catalyst</h2>
          <p className="panel-subtitle">Register catalysts, record catalysis events, and plan activations across the cognitive field</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive catalyst...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚗️ Cognitive Catalyst</h2>
        <p className="panel-subtitle">Register catalysts, record catalysis events, and plan activations across the cognitive field</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_catalysts ?? '-'}</span><span className="stat-label">Catalysts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_plans ?? '-'}</span><span className="stat-label">Plans</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_decays ?? '-'}</span><span className="stat-label">Decays</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_activity ?? '-'}</span><span className="stat-label">Avg Activity</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'catalyst', 'plan'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Catalyst Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Catalysts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_catalysts ?? 0}</div>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Decays</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_decays ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Activity</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_activity ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Catalysts</h3>
            <button onClick={() => loadCatalysts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {catalysts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No catalysts registered. Register one in the Catalyst section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {catalysts.slice(0, 10).map((c: any, i: number) => {
                  const id = c.catalyst_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>catalyst {id}{c.name ? ` · ${c.name}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.catalyst_type && renderBadge(c.catalyst_type, themeColors.secondary)}
                          {c.selectivity && renderBadge(c.selectivity, themeColors.primary)}
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

      {/* Catalyst Section */}
      {activeSection === 'catalyst' && (
        <div className="dashboard-section">
          {/* Register Catalyst */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Catalyst</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={catalystForm.agent_id} onChange={e => setCatalystForm({ ...catalystForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Catalyst Type</label>
                <select value={catalystForm.catalyst_type} onChange={e => setCatalystForm({ ...catalystForm, catalyst_type: e.target.value })}>
                  {CATALYST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Selectivity</label>
                <select value={catalystForm.selectivity} onChange={e => setCatalystForm({ ...catalystForm, selectivity: e.target.value })}>
                  {SELECTIVITY_LEVELS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Name *</label>
                <input value={catalystForm.name} onChange={e => setCatalystForm({ ...catalystForm, name: e.target.value })} placeholder="e.g. contrasting example" />
              </div>
            </div>
            <button onClick={handleRegisterCatalyst} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Catalyst</button>
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
                <label>Catalyst ID</label>
                <input value={eventForm.catalyst_id} onChange={e => setEventForm({ ...eventForm, catalyst_id: e.target.value })} placeholder="optional catalyst id" />
              </div>
              <div className="form-group">
                <label>Outcome</label>
                <select value={eventForm.outcome} onChange={e => setEventForm({ ...eventForm, outcome: e.target.value })}>
                  {CATALYSIS_OUTCOMES.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Activation</label>
                <select value={eventForm.activation} onChange={e => setEventForm({ ...eventForm, activation: e.target.value })}>
                  {ACTIVATION_STATES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRecordEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Event</button>
          </div>

          {/* Catalysts List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Catalysts ({catalysts.length})</h3>
            <button onClick={() => loadCatalysts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {catalysts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No catalysts registered. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {catalysts.slice(0, 30).map((c: any, i: number) => {
                  const id = c.catalyst_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>catalyst {id}{c.name ? ` · ${c.name}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.catalyst_type && renderBadge(c.catalyst_type, themeColors.secondary)}
                          {c.selectivity && renderBadge(c.selectivity, themeColors.primary)}
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>event {id}{e.catalyst_id ? ` · catalyst: ${e.catalyst_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.outcome && renderBadge(e.outcome, themeColors.secondary)}
                          {e.activation && renderBadge(e.activation, statusColor(e.activation))}
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
          {/* Plan Activation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Activation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Catalyst ID</label>
                <input value={planForm.catalyst_id} onChange={e => setPlanForm({ ...planForm, catalyst_id: e.target.value })} placeholder="optional catalyst id" />
              </div>
              <div className="form-group">
                <label>Target State</label>
                <select value={planForm.target_state} onChange={e => setPlanForm({ ...planForm, target_state: e.target.value })}>
                  {ACTIVATION_STATES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Selectivity</label>
                <select value={planForm.selectivity} onChange={e => setPlanForm({ ...planForm, selectivity: e.target.value })}>
                  {SELECTIVITY_LEVELS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handlePlanActivation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Activation</button>
          </div>

          {/* Record Decay */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Decay</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={decayForm.agent_id} onChange={e => setDecayForm({ ...decayForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Catalyst ID</label>
                <input value={decayForm.catalyst_id} onChange={e => setDecayForm({ ...decayForm, catalyst_id: e.target.value })} placeholder="optional catalyst id" />
              </div>
              <div className="form-group">
                <label>Regime</label>
                <select value={decayForm.regime} onChange={e => setDecayForm({ ...decayForm, regime: e.target.value })}>
                  {CATALYSIS_REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Decay Rate</label>
                <input value={decayForm.decay_rate} onChange={e => setDecayForm({ ...decayForm, decay_rate: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.3" />
              </div>
            </div>
            <button onClick={handleRecordDecay} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Decay</button>
            {decayResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(decayResult, null, 2)}</pre>
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
                  const id = p.plan_id ?? p.activation_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>plan {id}{p.catalyst_id ? ` · catalyst: ${p.catalyst_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.target_state && renderBadge(p.target_state, themeColors.secondary)}
                          {p.selectivity && renderBadge(p.selectivity, themeColors.primary)}
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

export default CognitiveCatalystPanel;
