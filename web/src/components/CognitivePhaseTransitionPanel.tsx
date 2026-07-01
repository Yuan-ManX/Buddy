import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: emerald for cognitive phase transition
const themeColors = {
  primary: '#059669',
  secondary: '#10b981',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

// Enum values must match backend TransitionPhase / ParameterType / CatalystType / TransitionStatus exactly (uppercase).
const TRANSITION_PHASES = ['STABLE', 'FLUCTUATING', 'CRITICAL', 'TRANSITIONING', 'REORGANIZING', 'NEW_STABLE'];
const PARAMETER_TYPES = ['COHERENCE', 'INTEGRATION', 'COMPLEXITY', 'CERTAINTY', 'FLUENCY', 'DIVERSITY'];
const CATALYST_TYPES = ['INSIGHT', 'CONTRADICTION', 'ANALOGY', 'EVIDENCE', 'REFLECTION', 'EXTERNAL'];
const TRANSITION_STATUS = ['DETECTED', 'PREDICTED', 'TRIGGERED', 'FACILITATED', 'STABILIZED', 'ABORTED'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  DETECTED: '#0ea5e9',
  PREDICTED: '#9ca3af',
  TRIGGERED: '#f59e0b',
  FACILITATED: '#059669',
  STABILIZED: '#16a34a',
  ABORTED: '#dc2626',
};

export const CognitivePhaseTransitionPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'context' | 'event'>('overview');

  // Contexts / events
  const [contexts, setContexts] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [detectResult, setDetectResult] = useState<any>(null);

  // Register context form
  const [contextForm, setContextForm] = useState({
    agent_id: '',
    domain: '',
    description: '',
  });

  // Record parameter form
  const [parameterForm, setParameterForm] = useState({
    context_id: '',
    parameter_type: 'COHERENCE',
    value: '0.5',
  });

  // Register catalyst form
  const [catalystForm, setCatalystForm] = useState({
    context_id: '',
    catalyst_type: 'INSIGHT',
    description: '',
    strength: '0.5',
  });

  // Detect critical point form
  const [detectForm, setDetectForm] = useState({ context_id: '' });

  // Trigger transition form
  const [triggerForm, setTriggerForm] = useState({
    context_id: '',
    catalyst_id: '',
    description: '',
  });

  // Facilitate transition form
  const [facilitateForm, setFacilitateForm] = useState({
    event_id: '',
    interventions: '',
  });

  // Stabilize phase form
  const [stabilizeForm, setStabilizeForm] = useState({
    event_id: '',
    description: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitivePhaseTransition.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive phase transition stats');
    } finally {
      setLoading(false);
    }
  };

  const loadContexts = async () => {
    try {
      const result = await api.cognitivePhaseTransition.listContexts();
      const list = Array.isArray(result) ? result : (result?.contexts ?? []);
      setContexts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load contexts');
    }
  };

  const loadEvents = async () => {
    try {
      const result = await api.cognitivePhaseTransition.listEvents();
      const list = Array.isArray(result) ? result : (result?.events ?? []);
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadContexts();
      loadEvents();
    }
  }, [activeSection]);

  const handleRegisterContext = async () => {
    if (!contextForm.agent_id.trim() || !contextForm.domain.trim()) {
      toast.error('Agent ID and domain are required');
      return;
    }
    const payload: any = {
      agent_id: contextForm.agent_id.trim(),
      domain: contextForm.domain.trim(),
    };
    if (contextForm.description.trim()) payload.description = contextForm.description.trim();
    try {
      await api.cognitivePhaseTransition.registerContext(payload);
      toast.success('Context registered');
      setContextForm({ agent_id: '', domain: '', description: '' });
      await loadContexts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordParameter = async () => {
    if (!parameterForm.context_id.trim()) {
      toast.error('Context ID is required');
      return;
    }
    const value = Number(parameterForm.value);
    if (Number.isNaN(value)) {
      toast.error('Value must be a number');
      return;
    }
    const payload: any = { parameter_type: parameterForm.parameter_type, value };
    try {
      await api.cognitivePhaseTransition.recordParameter(parameterForm.context_id.trim(), payload);
      toast.success('Parameter recorded');
      setParameterForm({ context_id: '', parameter_type: 'COHERENCE', value: '0.5' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRegisterCatalyst = async () => {
    if (!catalystForm.context_id.trim() || !catalystForm.description.trim()) {
      toast.error('Context ID and description are required');
      return;
    }
    const payload: any = {
      catalyst_type: catalystForm.catalyst_type,
      description: catalystForm.description.trim(),
    };
    if (catalystForm.strength.trim()) {
      const strength = Number(catalystForm.strength);
      if (!Number.isNaN(strength)) payload.strength = strength;
    }
    try {
      await api.cognitivePhaseTransition.registerCatalyst(catalystForm.context_id.trim(), payload);
      toast.success('Catalyst registered');
      setCatalystForm({ context_id: '', catalyst_type: 'INSIGHT', description: '', strength: '0.5' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDetect = async () => {
    if (!detectForm.context_id.trim()) {
      toast.error('Context ID is required');
      return;
    }
    try {
      const result = await api.cognitivePhaseTransition.detectCriticalPoint(detectForm.context_id.trim());
      setDetectResult(result);
      toast.success('Critical point detected');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTrigger = async () => {
    if (!triggerForm.context_id.trim() || !triggerForm.catalyst_id.trim()) {
      toast.error('Context ID and catalyst ID are required');
      return;
    }
    const payload: any = { catalyst_id: triggerForm.catalyst_id.trim() };
    if (triggerForm.description.trim()) payload.description = triggerForm.description.trim();
    try {
      await api.cognitivePhaseTransition.triggerTransition(triggerForm.context_id.trim(), payload);
      toast.success('Transition triggered');
      setTriggerForm({ context_id: '', catalyst_id: '', description: '' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFacilitate = async () => {
    if (!facilitateForm.event_id.trim()) {
      toast.error('Event ID is required');
      return;
    }
    const interventions = facilitateForm.interventions.split(',').map(s => s.trim()).filter(Boolean);
    try {
      await api.cognitivePhaseTransition.facilitateTransition(facilitateForm.event_id.trim(), interventions.length > 0 ? interventions : undefined);
      toast.success('Transition facilitated');
      setFacilitateForm({ event_id: '', interventions: '' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleStabilize = async () => {
    if (!stabilizeForm.event_id.trim()) {
      toast.error('Event ID is required');
      return;
    }
    const description = stabilizeForm.description.trim() || undefined;
    try {
      await api.cognitivePhaseTransition.stabilizePhase(stabilizeForm.event_id.trim(), description);
      toast.success('Phase stabilized');
      setStabilizeForm({ event_id: '', description: '' });
      await loadEvents();
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
          <h2>🌡️ Cognitive Phase Transition</h2>
          <p className="panel-subtitle">Track order parameters, detect critical points, and facilitate phase transitions</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive phase transition...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🌡️ Cognitive Phase Transition</h2>
        <p className="panel-subtitle">Track order parameters, detect critical points, and facilitate phase transitions</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_contexts ?? '-'}</span><span className="stat-label">Contexts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_catalysts ?? '-'}</span><span className="stat-label">Catalysts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_parameters ?? '-'}</span><span className="stat-label">Parameters</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.critical_points ?? '-'}</span><span className="stat-label">Critical Points</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'context', 'event'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Phase Transition Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Contexts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_contexts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_events ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Catalysts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_catalysts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Parameters</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_parameters ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Critical Points</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.critical_points ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Events</h3>
            <button onClick={() => loadEvents()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {events.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No events recorded. Trigger a transition in the Event section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {events.slice(0, 10).map((e: any, i: number) => {
                  const id = e.event_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{e.description ?? 'transition'} · {id}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>context: {e.context_id ?? '-'}</div>
                        </div>
                        <div>
                          {e.from_phase && renderBadge(e.from_phase, themeColors.secondary)}
                          {e.to_phase && renderBadge(e.to_phase, themeColors.primary)}
                          {e.status && renderBadge(e.status, statusColor(e.status))}
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

      {/* Context Section */}
      {activeSection === 'context' && (
        <div className="dashboard-section">
          {/* Register Context */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Context</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={contextForm.agent_id} onChange={e => setContextForm({ ...contextForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Domain *</label>
                <input value={contextForm.domain} onChange={e => setContextForm({ ...contextForm, domain: e.target.value })} placeholder="e.g. problem_solving" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={contextForm.description} onChange={e => setContextForm({ ...contextForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleRegisterContext} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Context</button>
          </div>

          {/* Record Parameter */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Parameter</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={parameterForm.context_id} onChange={e => setParameterForm({ ...parameterForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Parameter Type</label>
                <select value={parameterForm.parameter_type} onChange={e => setParameterForm({ ...parameterForm, parameter_type: e.target.value })}>
                  {PARAMETER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Value</label>
                <input value={parameterForm.value} onChange={e => setParameterForm({ ...parameterForm, value: e.target.value })} type="number" step="0.01" />
              </div>
            </div>
            <button onClick={handleRecordParameter} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Parameter</button>
          </div>

          {/* Register Catalyst */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Catalyst</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={catalystForm.context_id} onChange={e => setCatalystForm({ ...catalystForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Catalyst Type</label>
                <select value={catalystForm.catalyst_type} onChange={e => setCatalystForm({ ...catalystForm, catalyst_type: e.target.value })}>
                  {CATALYST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strength</label>
                <input value={catalystForm.strength} onChange={e => setCatalystForm({ ...catalystForm, strength: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description *</label>
                <input value={catalystForm.description} onChange={e => setCatalystForm({ ...catalystForm, description: e.target.value })} placeholder="Describe the catalyst" />
              </div>
            </div>
            <button onClick={handleRegisterCatalyst} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Catalyst</button>
          </div>

          {/* Detect Critical Point */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Detect Critical Point</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={detectForm.context_id} onChange={e => setDetectForm({ ...detectForm, context_id: e.target.value })} placeholder="context id" />
              </div>
            </div>
            <button onClick={handleDetect} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Detect</button>
            {detectResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(detectResult, null, 2)}</pre>
            )}
          </div>

          {/* Contexts List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Contexts ({contexts.length})</h3>
            <button onClick={() => loadContexts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {contexts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No contexts recorded. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {contexts.slice(0, 30).map((c: any, i: number) => {
                  const id = c.context_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{c.domain ?? 'no_domain'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                      {c.description && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{c.description}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Event Section */}
      {activeSection === 'event' && (
        <div className="dashboard-section">
          {/* Trigger Transition */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Trigger Transition</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={triggerForm.context_id} onChange={e => setTriggerForm({ ...triggerForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Catalyst ID *</label>
                <input value={triggerForm.catalyst_id} onChange={e => setTriggerForm({ ...triggerForm, catalyst_id: e.target.value })} placeholder="catalyst id" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={triggerForm.description} onChange={e => setTriggerForm({ ...triggerForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleTrigger} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Trigger Transition</button>
          </div>

          {/* Facilitate Transition */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Facilitate Transition</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Event ID *</label>
                <input value={facilitateForm.event_id} onChange={e => setFacilitateForm({ ...facilitateForm, event_id: e.target.value })} placeholder="event id" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Interventions (comma-separated)</label>
                <input value={facilitateForm.interventions} onChange={e => setFacilitateForm({ ...facilitateForm, interventions: e.target.value })} placeholder="e.g. scaffold_hint, analogy_seed" />
              </div>
            </div>
            <button onClick={handleFacilitate} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Facilitate</button>
          </div>

          {/* Stabilize Phase */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Stabilize Phase</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Event ID *</label>
                <input value={stabilizeForm.event_id} onChange={e => setStabilizeForm({ ...stabilizeForm, event_id: e.target.value })} placeholder="event id" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={stabilizeForm.description} onChange={e => setStabilizeForm({ ...stabilizeForm, description: e.target.value })} placeholder="Optional description of stabilization" />
              </div>
            </div>
            <button onClick={handleStabilize} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Stabilize</button>
          </div>

          {/* Events List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Events ({events.length})</h3>
            <button onClick={() => loadEvents()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {events.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No events recorded. Trigger a transition above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {events.slice(0, 30).map((e: any, i: number) => {
                  const id = e.event_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{e.description ?? 'transition'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>context: {e.context_id ?? '-'} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.from_phase && renderBadge(e.from_phase, themeColors.secondary)}
                          {e.to_phase && renderBadge(e.to_phase, themeColors.primary)}
                          {e.status && renderBadge(e.status, statusColor(e.status))}
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

export default CognitivePhaseTransitionPanel;
