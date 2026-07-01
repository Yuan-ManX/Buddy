import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: violet for cognitive tension
const themeColors = {
  primary: '#7c3aed',
  secondary: '#8b5cf6',
  bg: '#f5f3ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

// Enum values must match backend TensionKind / TensionState / ResolutionMode / TensionPolarity / HoldingStrategy exactly (uppercase).
const TENSION_KINDS = ['DIALECTIC', 'PARADOXICAL', 'COMPETING', 'CONFLICTING', 'AMBIVALENT', 'COMPLEMENTARY'];
const TENSION_STATES = ['LATENT', 'ACKNOWLEDGED', 'HELD', 'RESOLVING', 'RESOLVED', 'DISSOLVED'];
const RESOLUTION_MODES = ['SYNTHESIS', 'SELECTION', 'COMPROMISE', 'TRANSCENDENCE', 'DISSOLUTION', 'DEFER'];
const TENSION_POLARITIES = ['POSITIVE', 'NEGATIVE', 'NEUTRAL', 'MIXED'];
const HOLDING_STRATEGIES = ['HOLD_AND_OBSERVE', 'ROTATE_ATTENTION', 'DEEPLY_CONSIDER', 'SEEK_CONTEXT', 'ARTICULATE', 'ENACT'];

// Map a tension state value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  LATENT: '#9ca3af',
  ACKNOWLEDGED: '#0ea5e9',
  HELD: '#8b5cf6',
  RESOLVING: '#f59e0b',
  RESOLVED: '#16a34a',
  DISSOLVED: '#0d9488',
};

export const CognitiveTensionPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'pole' | 'resolution'>('overview');

  // Poles / pairs / resolutions
  const [poles, setPoles] = useState<any[]>([]);
  const [pairs, setPairs] = useState<any[]>([]);
  const [resolutions, setResolutions] = useState<any[]>([]);
  const [holdingResult, setHoldingResult] = useState<any>(null);

  // Register pole form
  const [poleForm, setPoleForm] = useState({
    agent_id: '',
    content: '',
    polarity: 'NEUTRAL',
    weight: '',
  });

  // Form pair form
  const [pairForm, setPairForm] = useState({
    agent_id: '',
    pole_a_id: '',
    pole_b_id: '',
    kind: 'DIALECTIC',
  });

  // Attempt resolution form
  const [resolutionForm, setResolutionForm] = useState({
    agent_id: '',
    pair_id: '',
    mode: 'SYNTHESIS',
    synthesis: '',
  });

  // Decide holding form
  const [holdingForm, setHoldingForm] = useState({
    agent_id: '',
    pair_id: '',
    strategy: 'HOLD_AND_OBSERVE',
    duration: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveTension.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive tension stats');
    } finally {
      setLoading(false);
    }
  };

  const loadPoles = async () => {
    try {
      const result = await api.cognitiveTension.listPoles();
      const list = Array.isArray(result) ? result : (result?.poles ?? []);
      setPoles(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load poles');
    }
  };

  const loadPairs = async () => {
    try {
      const result = await api.cognitiveTension.listPairs();
      const list = Array.isArray(result) ? result : (result?.pairs ?? []);
      setPairs(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load pairs');
    }
  };

  const loadResolutions = async () => {
    try {
      const result = await api.cognitiveTension.listResolutions();
      const list = Array.isArray(result) ? result : (result?.resolutions ?? []);
      setResolutions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load resolutions');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadPoles();
      loadPairs();
      loadResolutions();
    }
  }, [activeSection]);

  const handleRegisterPole = async () => {
    if (!poleForm.agent_id.trim() || !poleForm.content.trim()) {
      toast.error('Agent ID and content are required');
      return;
    }
    const payload: any = {
      agent_id: poleForm.agent_id.trim(),
      content: poleForm.content.trim(),
      polarity: poleForm.polarity,
    };
    if (poleForm.weight.trim()) payload.weight = Number(poleForm.weight);
    try {
      await api.cognitiveTension.registerPole(payload);
      toast.success('Pole registered');
      setPoleForm({ agent_id: '', content: '', polarity: 'NEUTRAL', weight: '' });
      await loadPoles();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFormPair = async () => {
    if (!pairForm.agent_id.trim() || !pairForm.pole_a_id.trim() || !pairForm.pole_b_id.trim()) {
      toast.error('Agent ID and both pole IDs are required');
      return;
    }
    const payload: any = {
      agent_id: pairForm.agent_id.trim(),
      pole_a_id: pairForm.pole_a_id.trim(),
      pole_b_id: pairForm.pole_b_id.trim(),
      kind: pairForm.kind,
    };
    try {
      await api.cognitiveTension.formPair(payload);
      toast.success('Pair formed');
      setPairForm({ agent_id: '', pole_a_id: '', pole_b_id: '', kind: 'DIALECTIC' });
      await loadPairs();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAttemptResolution = async () => {
    if (!resolutionForm.agent_id.trim() || !resolutionForm.pair_id.trim()) {
      toast.error('Agent ID and pair ID are required');
      return;
    }
    const payload: any = {
      agent_id: resolutionForm.agent_id.trim(),
      pair_id: resolutionForm.pair_id.trim(),
      mode: resolutionForm.mode,
    };
    if (resolutionForm.synthesis.trim()) payload.synthesis = resolutionForm.synthesis.trim();
    try {
      await api.cognitiveTension.attemptResolution(payload);
      toast.success('Resolution attempted');
      setResolutionForm({ agent_id: '', pair_id: '', mode: 'SYNTHESIS', synthesis: '' });
      await loadResolutions();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDecideHolding = async () => {
    if (!holdingForm.agent_id.trim() || !holdingForm.pair_id.trim()) {
      toast.error('Agent ID and pair ID are required');
      return;
    }
    const payload: any = {
      agent_id: holdingForm.agent_id.trim(),
      pair_id: holdingForm.pair_id.trim(),
      strategy: holdingForm.strategy,
    };
    if (holdingForm.duration.trim()) payload.duration = Number(holdingForm.duration);
    try {
      const result = await api.cognitiveTension.decideHolding(payload);
      setHoldingResult(result);
      toast.success('Holding decided');
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
          <h2>⚡ Cognitive Tension</h2>
          <p className="panel-subtitle">Register poles, form pairs, and attempt resolutions between opposing ideas</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive tension...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚡ Cognitive Tension</h2>
        <p className="panel-subtitle">Register poles, form pairs, and attempt resolutions between opposing ideas</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_poles ?? '-'}</span><span className="stat-label">Poles</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_pairs ?? '-'}</span><span className="stat-label">Pairs</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_resolutions ?? '-'}</span><span className="stat-label">Resolutions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_holdings ?? '-'}</span><span className="stat-label">Holdings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_tension ?? '-'}</span><span className="stat-label">Avg Tension</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'pole', 'resolution'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Tension Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Poles</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_poles ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Pairs</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_pairs ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Resolutions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_resolutions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Holdings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_holdings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Tension</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_tension ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Poles</h3>
            <button onClick={() => loadPoles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {poles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No poles registered. Register one in the Pole section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {poles.slice(0, 10).map((p: any, i: number) => {
                  const id = p.pole_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>pole {id}{p.content ? ` · ${p.content}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.polarity && renderBadge(p.polarity, themeColors.secondary)}
                          {p.weight != null && renderBadge(`weight: ${p.weight}`, themeColors.primary)}
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

      {/* Pole Section */}
      {activeSection === 'pole' && (
        <div className="dashboard-section">
          {/* Register Pole */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Pole</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={poleForm.agent_id} onChange={e => setPoleForm({ ...poleForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Polarity</label>
                <select value={poleForm.polarity} onChange={e => setPoleForm({ ...poleForm, polarity: e.target.value })}>
                  {TENSION_POLARITIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Weight</label>
                <input value={poleForm.weight} onChange={e => setPoleForm({ ...poleForm, weight: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Content *</label>
                <input value={poleForm.content} onChange={e => setPoleForm({ ...poleForm, content: e.target.value })} placeholder="e.g. explore boldly" />
              </div>
            </div>
            <button onClick={handleRegisterPole} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Pole</button>
          </div>

          {/* Form Pair */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Form Pair</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={pairForm.agent_id} onChange={e => setPairForm({ ...pairForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Pole A ID *</label>
                <input value={pairForm.pole_a_id} onChange={e => setPairForm({ ...pairForm, pole_a_id: e.target.value })} placeholder="first pole id" />
              </div>
              <div className="form-group">
                <label>Pole B ID *</label>
                <input value={pairForm.pole_b_id} onChange={e => setPairForm({ ...pairForm, pole_b_id: e.target.value })} placeholder="second pole id" />
              </div>
              <div className="form-group">
                <label>Kind</label>
                <select value={pairForm.kind} onChange={e => setPairForm({ ...pairForm, kind: e.target.value })}>
                  {TENSION_KINDS.map(k => <option key={k} value={k}>{k}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleFormPair} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Form Pair</button>
          </div>

          {/* Poles List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Poles ({poles.length})</h3>
            <button onClick={() => loadPoles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {poles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No poles registered. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {poles.slice(0, 30).map((p: any, i: number) => {
                  const id = p.pole_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>pole {id}{p.content ? ` · ${p.content}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.polarity && renderBadge(p.polarity, themeColors.secondary)}
                          {p.weight != null && renderBadge(`weight: ${p.weight}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Pairs List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Pairs ({pairs.length})</h3>
            <button onClick={() => loadPairs()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {pairs.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No pairs formed. Form one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {pairs.slice(0, 30).map((p: any, i: number) => {
                  const id = p.pair_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>pair {id}{p.pole_a_id ? ` · ${p.pole_a_id}` : ''}{p.pole_b_id ? ` <-> ${p.pole_b_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.kind && renderBadge(p.kind, themeColors.secondary)}
                          {p.state && renderBadge(p.state, statusColor(p.state))}
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

      {/* Resolution Section */}
      {activeSection === 'resolution' && (
        <div className="dashboard-section">
          {/* Attempt Resolution */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Attempt Resolution</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={resolutionForm.agent_id} onChange={e => setResolutionForm({ ...resolutionForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Pair ID *</label>
                <input value={resolutionForm.pair_id} onChange={e => setResolutionForm({ ...resolutionForm, pair_id: e.target.value })} placeholder="pair id" />
              </div>
              <div className="form-group">
                <label>Mode</label>
                <select value={resolutionForm.mode} onChange={e => setResolutionForm({ ...resolutionForm, mode: e.target.value })}>
                  {RESOLUTION_MODES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Synthesis</label>
                <input value={resolutionForm.synthesis} onChange={e => setResolutionForm({ ...resolutionForm, synthesis: e.target.value })} placeholder="optional synthesized outcome" />
              </div>
            </div>
            <button onClick={handleAttemptResolution} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Attempt Resolution</button>
          </div>

          {/* Decide Holding */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Decide Holding</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={holdingForm.agent_id} onChange={e => setHoldingForm({ ...holdingForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Pair ID *</label>
                <input value={holdingForm.pair_id} onChange={e => setHoldingForm({ ...holdingForm, pair_id: e.target.value })} placeholder="pair id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={holdingForm.strategy} onChange={e => setHoldingForm({ ...holdingForm, strategy: e.target.value })}>
                  {HOLDING_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Duration</label>
                <input value={holdingForm.duration} onChange={e => setHoldingForm({ ...holdingForm, duration: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 5.0" />
              </div>
            </div>
            <button onClick={handleDecideHolding} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Decide Holding</button>
            {holdingResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(holdingResult, null, 2)}</pre>
            )}
          </div>

          {/* Resolutions List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Resolutions ({resolutions.length})</h3>
            <button onClick={() => loadResolutions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {resolutions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No resolutions attempted. Attempt one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {resolutions.slice(0, 30).map((r: any, i: number) => {
                  const id = r.resolution_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>resolution {id}{r.pair_id ? ` · pair: ${r.pair_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.mode && renderBadge(r.mode, themeColors.secondary)}
                          {r.state && renderBadge(r.state, statusColor(r.state))}
                        </div>
                      </div>
                      {r.synthesis && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{r.synthesis}</div>
                      )}
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

export default CognitiveTensionPanel;
