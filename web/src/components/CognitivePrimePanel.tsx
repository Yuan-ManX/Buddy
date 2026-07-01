import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: violet for cognitive prime
const themeColors = {
  primary: '#7c3aed',
  secondary: '#8b5cf6',
  bg: '#f5f3ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

// Enum values must match backend PrimeType / PrimeStrength / ActivationMode / EffectDirection exactly (uppercase).
const PRIME_TYPES = ['SEMANTIC', 'ASSOCIATIVE', 'AFFECTIVE', 'GOAL', 'PERCEPTUAL', 'CONCEPTUAL'];
const PRIME_STRENGTHS = ['SUBTLE', 'MODERATE', 'STRONG', 'OVERWHELMING'];
const ACTIVATION_MODES = ['SPREADING', 'FOCUSED', 'DIFFUSE', 'CASCADE'];
const EFFECT_DIRECTIONS = ['POSITIVE', 'NEGATIVE', 'NEUTRAL'];

// Map a strength value to a badge color for at-a-glance scanning.
const STRENGTH_COLORS: Record<string, string> = {
  SUBTLE: '#9ca3af',
  MODERATE: '#7c3aed',
  STRONG: '#6d28d9',
  OVERWHELMING: '#dc2626',
};

export const CognitivePrimePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'context' | 'activation'>('overview');

  // Contexts / activations / sessions
  const [contexts, setContexts] = useState<any[]>([]);
  const [activations, setActivations] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [spreadResult, setSpreadResult] = useState<any>(null);
  const [effectResult, setEffectResult] = useState<any>(null);
  const [interferenceResult, setInterferenceResult] = useState<any>(null);

  // Register context form
  const [contextForm, setContextForm] = useState({
    agent_id: '',
    description: '',
    active_concepts: '',
  });

  // Activate prime form
  const [activateForm, setActivateForm] = useState({
    context_id: '',
    prime_concept: '',
    prime_type: 'SEMANTIC',
    strength: 'MODERATE',
    description: '',
  });

  // Spread activation form
  const [spreadForm, setSpreadForm] = useState({
    activation_id: '',
    mode: 'SPREADING',
    fan_out: '5',
    decay: '0.2',
  });

  // Measure effect form
  const [effectForm, setEffectForm] = useState({
    activation_id: '',
    target_concept: '',
    direction: 'POSITIVE',
  });

  // Interference form
  const [interferenceForm, setInterferenceForm] = useState({
    activation_id: '',
    other_activation_id: '',
  });

  // Session form
  const [sessionForm, setSessionForm] = useState({
    context_id: '',
    goal: '',
    description: '',
  });

  // Decay form
  const [decayForm, setDecayForm] = useState({
    context_id: '',
    decay_factor: '0.5',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitivePrime.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive prime stats');
    } finally {
      setLoading(false);
    }
  };

  const loadContexts = async () => {
    try {
      const result = await api.cognitivePrime.listContexts();
      const list = Array.isArray(result) ? result : (result?.contexts ?? []);
      setContexts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load contexts');
    }
  };

  const loadSessions = async () => {
    try {
      const list: any[] = [];
      // Sessions are scoped per context; aggregate across loaded contexts.
      for (const c of contexts) {
        const cid = c.context_id ?? c.id;
        if (!cid) continue;
        try {
          const result = await api.cognitivePrime.listSessions(cid);
          const partial = Array.isArray(result) ? result : (result?.sessions ?? []);
          list.push(...partial);
        } catch { /* skip contexts without sessions */ }
      }
      setSessions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load sessions');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + contexts when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadContexts();
    }
  }, [activeSection]);

  // After contexts are loaded, aggregate sessions for the overview list
  useEffect(() => {
    if (activeSection === 'overview' && contexts.length > 0) {
      loadSessions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contexts, activeSection]);

  const handleRegisterContext = async () => {
    if (!contextForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = { agent_id: contextForm.agent_id.trim() };
    if (contextForm.description.trim()) payload.description = contextForm.description.trim();
    if (contextForm.active_concepts.trim()) {
      const concepts = contextForm.active_concepts.split(',').map(s => s.trim()).filter(Boolean);
      if (concepts.length > 0) payload.active_concepts = concepts;
    }
    try {
      await api.cognitivePrime.registerContext(payload);
      toast.success('Context registered');
      setContextForm({ agent_id: '', description: '', active_concepts: '' });
      await loadContexts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleActivatePrime = async () => {
    if (!activateForm.context_id.trim() || !activateForm.prime_concept.trim()) {
      toast.error('Context ID and prime concept are required');
      return;
    }
    const payload: any = {
      prime_concept: activateForm.prime_concept.trim(),
      prime_type: activateForm.prime_type,
      strength: activateForm.strength,
    };
    if (activateForm.description.trim()) payload.description = activateForm.description.trim();
    try {
      await api.cognitivePrime.activatePrime(activateForm.context_id.trim(), payload);
      toast.success('Prime activated');
      setActivateForm({ context_id: '', prime_concept: '', prime_type: 'SEMANTIC', strength: 'MODERATE', description: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSpread = async () => {
    if (!spreadForm.activation_id.trim()) {
      toast.error('Activation ID is required');
      return;
    }
    const payload: any = { mode: spreadForm.mode };
    if (spreadForm.fan_out.trim()) payload.fan_out = Number(spreadForm.fan_out);
    if (spreadForm.decay.trim()) payload.decay = Number(spreadForm.decay);
    try {
      const result = await api.cognitivePrime.spreadActivation(spreadForm.activation_id.trim(), payload);
      setSpreadResult(result);
      toast.success('Activation spread');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMeasureEffect = async () => {
    if (!effectForm.activation_id.trim() || !effectForm.target_concept.trim()) {
      toast.error('Activation ID and target concept are required');
      return;
    }
    const payload: any = { target_concept: effectForm.target_concept.trim(), direction: effectForm.direction };
    try {
      const result = await api.cognitivePrime.measureEffect(effectForm.activation_id.trim(), payload);
      setEffectResult(result);
      toast.success('Effect measured');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleInterference = async () => {
    if (!interferenceForm.activation_id.trim() || !interferenceForm.other_activation_id.trim()) {
      toast.error('Both activation IDs are required');
      return;
    }
    try {
      const result = await api.cognitivePrime.checkInterference(interferenceForm.activation_id.trim(), interferenceForm.other_activation_id.trim());
      setInterferenceResult(result);
      toast.success('Interference checked');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateSession = async () => {
    if (!sessionForm.context_id.trim()) {
      toast.error('Context ID is required');
      return;
    }
    const payload: any = {};
    if (sessionForm.goal.trim()) payload.goal = sessionForm.goal.trim();
    if (sessionForm.description.trim()) payload.description = sessionForm.description.trim();
    try {
      await api.cognitivePrime.createSession(sessionForm.context_id.trim(), payload);
      toast.success('Session created');
      setSessionForm({ context_id: '', goal: '', description: '' });
      await loadSessions();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDecay = async () => {
    if (!decayForm.context_id.trim()) {
      toast.error('Context ID is required');
      return;
    }
    const decayFactor = decayForm.decay_factor.trim() ? Number(decayForm.decay_factor) : undefined;
    try {
      await api.cognitivePrime.decayActivations(decayForm.context_id.trim(), decayFactor);
      toast.success('Activations decayed');
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

  const strengthColor = (s: string) => STRENGTH_COLORS[s] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>⚡ Cognitive Prime</h2>
          <p className="panel-subtitle">Register priming contexts, activate concepts, and measure spreading effects</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive prime...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚡ Cognitive Prime</h2>
        <p className="panel-subtitle">Register priming contexts, activate concepts, and measure spreading effects</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_contexts ?? '-'}</span><span className="stat-label">Contexts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_activations ?? '-'}</span><span className="stat-label">Activations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_effects ?? '-'}</span><span className="stat-label">Effects</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_sessions ?? '-'}</span><span className="stat-label">Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_activations ?? '-'}</span><span className="stat-label">Active</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'context', 'activation'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Prime Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Contexts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_contexts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Activations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_activations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Effects</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_effects ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Sessions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_sessions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Activations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_activations ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Contexts</h3>
            <button onClick={() => loadContexts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {contexts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No contexts recorded. Register one in the Context section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {contexts.slice(0, 10).map((c: any, i: number) => {
                  const id = c.context_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{c.description ?? ''} · {id}</div>
                      {Array.isArray(c.active_concepts) && c.active_concepts.length > 0 && (
                        <div style={{ marginTop: 4 }}>{c.active_concepts.map((k: string) => renderBadge(k, themeColors.secondary))}</div>
                      )}
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
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Context</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={contextForm.agent_id} onChange={e => setContextForm({ ...contextForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={contextForm.description} onChange={e => setContextForm({ ...contextForm, description: e.target.value })} placeholder="Optional description" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Active Concepts (comma-separated)</label>
                <input value={contextForm.active_concepts} onChange={e => setContextForm({ ...contextForm, active_concepts: e.target.value })} placeholder="e.g. creativity, exploration" />
              </div>
            </div>
            <button onClick={handleRegisterContext} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Context</button>
          </div>

          {/* Create Session */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Session</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={sessionForm.context_id} onChange={e => setSessionForm({ ...sessionForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Goal</label>
                <input value={sessionForm.goal} onChange={e => setSessionForm({ ...sessionForm, goal: e.target.value })} placeholder="e.g. creative_generation" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={sessionForm.description} onChange={e => setSessionForm({ ...sessionForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleCreateSession} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Session</button>
          </div>

          {/* Decay */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Decay Activations</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={decayForm.context_id} onChange={e => setDecayForm({ ...decayForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Decay Factor</label>
                <input value={decayForm.decay_factor} onChange={e => setDecayForm({ ...decayForm, decay_factor: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
            </div>
            <button onClick={handleDecay} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Decay</button>
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
                      <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
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

      {/* Activation Section */}
      {activeSection === 'activation' && (
        <div className="dashboard-section">
          {/* Activate Prime */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Activate Prime</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={activateForm.context_id} onChange={e => setActivateForm({ ...activateForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Prime Concept *</label>
                <input value={activateForm.prime_concept} onChange={e => setActivateForm({ ...activateForm, prime_concept: e.target.value })} placeholder="e.g. risk_awareness" />
              </div>
              <div className="form-group">
                <label>Prime Type</label>
                <select value={activateForm.prime_type} onChange={e => setActivateForm({ ...activateForm, prime_type: e.target.value })}>
                  {PRIME_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strength</label>
                <select value={activateForm.strength} onChange={e => setActivateForm({ ...activateForm, strength: e.target.value })}>
                  {PRIME_STRENGTHS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={activateForm.description} onChange={e => setActivateForm({ ...activateForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleActivatePrime} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Activate Prime</button>
          </div>

          {/* Spread Activation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Spread Activation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Activation ID *</label>
                <input value={spreadForm.activation_id} onChange={e => setSpreadForm({ ...spreadForm, activation_id: e.target.value })} placeholder="activation id" />
              </div>
              <div className="form-group">
                <label>Mode</label>
                <select value={spreadForm.mode} onChange={e => setSpreadForm({ ...spreadForm, mode: e.target.value })}>
                  {ACTIVATION_MODES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Fan Out</label>
                <input value={spreadForm.fan_out} onChange={e => setSpreadForm({ ...spreadForm, fan_out: e.target.value })} type="number" min="1" />
              </div>
              <div className="form-group">
                <label>Decay</label>
                <input value={spreadForm.decay} onChange={e => setSpreadForm({ ...spreadForm, decay: e.target.value })} type="number" min="0" max="1" step="0.05" />
              </div>
            </div>
            <button onClick={handleSpread} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Spread</button>
            {spreadResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(spreadResult, null, 2)}</pre>
            )}
          </div>

          {/* Measure Effect */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Measure Effect</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Activation ID *</label>
                <input value={effectForm.activation_id} onChange={e => setEffectForm({ ...effectForm, activation_id: e.target.value })} placeholder="activation id" />
              </div>
              <div className="form-group">
                <label>Target Concept *</label>
                <input value={effectForm.target_concept} onChange={e => setEffectForm({ ...effectForm, target_concept: e.target.value })} placeholder="target concept" />
              </div>
              <div className="form-group">
                <label>Direction</label>
                <select value={effectForm.direction} onChange={e => setEffectForm({ ...effectForm, direction: e.target.value })}>
                  {EFFECT_DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleMeasureEffect} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Measure</button>
            {effectResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(effectResult, null, 2)}</pre>
            )}
          </div>

          {/* Interference */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Check Interference</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Activation ID *</label>
                <input value={interferenceForm.activation_id} onChange={e => setInterferenceForm({ ...interferenceForm, activation_id: e.target.value })} placeholder="activation id" />
              </div>
              <div className="form-group">
                <label>Other Activation ID *</label>
                <input value={interferenceForm.other_activation_id} onChange={e => setInterferenceForm({ ...interferenceForm, other_activation_id: e.target.value })} placeholder="other activation id" />
              </div>
            </div>
            <button onClick={handleInterference} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Check Interference</button>
            {interferenceResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(interferenceResult, null, 2)}</pre>
            )}
          </div>

          {/* Sessions List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Sessions ({sessions.length})</h3>
            <button onClick={() => loadSessions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {sessions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No sessions recorded. Create one in the Context section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {sessions.slice(0, 30).map((s: any, i: number) => {
                  const id = s.session_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{s.goal ?? 'no_goal'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{id}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>context: {s.context_id ?? '-'}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Activations List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Activations ({activations.length})</h3>
            {activations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No activations loaded. Activate a prime above to populate via spread.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {activations.slice(0, 30).map((a: any, i: number) => {
                  const id = a.activation_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{a.prime_concept ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.prime_type && renderBadge(a.prime_type, themeColors.secondary)}
                          {a.strength && renderBadge(a.strength, strengthColor(a.strength))}
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

export default CognitivePrimePanel;
