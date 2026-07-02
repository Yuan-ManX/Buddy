import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: amber for cognitive symbology
const themeColors = {
  primary: '#d97706',
  secondary: '#f59e0b',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

// Enum values must match backend SymbolType / SymbolicDensity / SymbolicOperation / EncodingOutcome / TransformationRegime exactly (uppercase).
const SYMBOL_TYPES = ['ICON', 'INDEX', 'TOKEN', 'METAPHOR', 'METONYM', 'ABSTRACT'];
const SYMBOLIC_DENSITIES = ['SPARSE', 'MODERATE', 'DENSE', 'SATURATED', 'BARREN'];
const SYMBOLIC_OPERATIONS = ['SUBSTITUTE', 'COMBINE', 'DECOMPOSE', 'ABSTRACT', 'INSTANTIATE', 'TRANSFORM'];
const ENCODING_OUTCOMES = ['SUCCESS', 'PARTIAL', 'AMBIGUOUS', 'FAILED', 'REDUNDANT'];
const TRANSFORMATION_REGIMES = ['DORMANT', 'OCCASIONAL', 'ACTIVE', 'FLUID', 'TURBULENT'];

// Map a transformation regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  DORMANT: '#9ca3af',
  OCCASIONAL: '#0ea5e9',
  ACTIVE: '#d97706',
  FLUID: '#059669',
  TURBULENT: '#dc2626',
};

export const CognitiveSymbologyPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'symbol' | 'trace'>('overview');

  // Symbols / actions / encodings
  const [symbols, setSymbols] = useState<any[]>([]);
  const [actions, setActions] = useState<any[]>([]);
  const [encodings, setEncodings] = useState<any[]>([]);
  const [traceResult, setTraceResult] = useState<any>(null);

  // Register symbol form
  const [symbolForm, setSymbolForm] = useState({
    agent_id: '',
    content: '',
    symbol_type: 'ICON',
    density: 'MODERATE',
  });

  // Perform action form
  const [actionForm, setActionForm] = useState({
    agent_id: '',
    symbol_id: '',
    operation: 'SUBSTITUTE',
    rationale: '',
  });

  // Attempt encoding form
  const [encodingForm, setEncodingForm] = useState({
    agent_id: '',
    symbol_id: '',
    target: '',
    outcome: 'SUCCESS',
  });

  // Trace transformation form
  const [traceForm, setTraceForm] = useState({
    agent_id: '',
    symbol_id: '',
    regime: 'DORMANT',
    velocity: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveSymbology.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive symbology stats');
    } finally {
      setLoading(false);
    }
  };

  const loadSymbols = async () => {
    try {
      const result = await api.cognitiveSymbology.listSymbols();
      const list = Array.isArray(result) ? result : (result?.symbols ?? []);
      setSymbols(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load symbols');
    }
  };

  const loadActions = async () => {
    try {
      const result = await api.cognitiveSymbology.listActions();
      const list = Array.isArray(result) ? result : (result?.actions ?? []);
      setActions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load actions');
    }
  };

  const loadEncodings = async () => {
    try {
      const result = await api.cognitiveSymbology.listEncodings();
      const list = Array.isArray(result) ? result : (result?.encodings ?? []);
      setEncodings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load encodings');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadSymbols();
      loadActions();
      loadEncodings();
    }
  }, [activeSection]);

  const handleRegisterSymbol = async () => {
    if (!symbolForm.agent_id.trim() || !symbolForm.content.trim()) {
      toast.error('Agent ID and content are required');
      return;
    }
    const payload: any = {
      agent_id: symbolForm.agent_id.trim(),
      content: symbolForm.content.trim(),
      symbol_type: symbolForm.symbol_type,
      density: symbolForm.density,
    };
    try {
      await api.cognitiveSymbology.registerSymbol(payload);
      toast.success('Symbol registered');
      setSymbolForm({ agent_id: '', content: '', symbol_type: 'ICON', density: 'MODERATE' });
      await loadSymbols();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePerformAction = async () => {
    if (!actionForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: actionForm.agent_id.trim(),
      operation: actionForm.operation,
    };
    if (actionForm.symbol_id.trim()) payload.symbol_id = actionForm.symbol_id.trim();
    if (actionForm.rationale.trim()) payload.rationale = actionForm.rationale.trim();
    try {
      await api.cognitiveSymbology.performAction(payload);
      toast.success('Action performed');
      setActionForm({ agent_id: '', symbol_id: '', operation: 'SUBSTITUTE', rationale: '' });
      await loadActions();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAttemptEncoding = async () => {
    if (!encodingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: encodingForm.agent_id.trim(),
      outcome: encodingForm.outcome,
    };
    if (encodingForm.symbol_id.trim()) payload.symbol_id = encodingForm.symbol_id.trim();
    if (encodingForm.target.trim()) payload.target = encodingForm.target.trim();
    try {
      await api.cognitiveSymbology.attemptEncoding(payload);
      toast.success('Encoding attempted');
      setEncodingForm({ agent_id: '', symbol_id: '', target: '', outcome: 'SUCCESS' });
      await loadEncodings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTraceTransformation = async () => {
    if (!traceForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: traceForm.agent_id.trim(),
      regime: traceForm.regime,
    };
    if (traceForm.symbol_id.trim()) payload.symbol_id = traceForm.symbol_id.trim();
    if (traceForm.velocity.trim()) payload.velocity = Number(traceForm.velocity);
    try {
      const result = await api.cognitiveSymbology.traceTransformation(payload);
      setTraceResult(result);
      toast.success('Transformation traced');
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
          <h2>🔣 Cognitive Symbology</h2>
          <p className="panel-subtitle">Register symbols, perform operations, and trace transformations across representational layers</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive symbology...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔣 Cognitive Symbology</h2>
        <p className="panel-subtitle">Register symbols, perform operations, and trace transformations across representational layers</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_symbols ?? '-'}</span><span className="stat-label">Symbols</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_actions ?? '-'}</span><span className="stat-label">Actions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_encodings ?? '-'}</span><span className="stat-label">Encodings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_traces ?? '-'}</span><span className="stat-label">Traces</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_density ?? '-'}</span><span className="stat-label">Avg Density</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'symbol', 'trace'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Symbology Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Symbols</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_symbols ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Actions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_actions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Encodings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_encodings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Traces</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_traces ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Density</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_density ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Symbols</h3>
            <button onClick={() => loadSymbols()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {symbols.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No symbols registered. Register one in the Symbol section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {symbols.slice(0, 10).map((s: any, i: number) => {
                  const id = s.symbol_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>symbol {id}{s.content ? ` · ${s.content}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.symbol_type && renderBadge(s.symbol_type, themeColors.secondary)}
                          {s.density && renderBadge(s.density, themeColors.primary)}
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

      {/* Symbol Section */}
      {activeSection === 'symbol' && (
        <div className="dashboard-section">
          {/* Register Symbol */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Symbol</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={symbolForm.agent_id} onChange={e => setSymbolForm({ ...symbolForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Symbol Type</label>
                <select value={symbolForm.symbol_type} onChange={e => setSymbolForm({ ...symbolForm, symbol_type: e.target.value })}>
                  {SYMBOL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Density</label>
                <select value={symbolForm.density} onChange={e => setSymbolForm({ ...symbolForm, density: e.target.value })}>
                  {SYMBOLIC_DENSITIES.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Content *</label>
                <input value={symbolForm.content} onChange={e => setSymbolForm({ ...symbolForm, content: e.target.value })} placeholder="e.g. lightbulb as idea" />
              </div>
            </div>
            <button onClick={handleRegisterSymbol} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Symbol</button>
          </div>

          {/* Perform Action */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Perform Action</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={actionForm.agent_id} onChange={e => setActionForm({ ...actionForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Symbol ID</label>
                <input value={actionForm.symbol_id} onChange={e => setActionForm({ ...actionForm, symbol_id: e.target.value })} placeholder="optional symbol id" />
              </div>
              <div className="form-group">
                <label>Operation</label>
                <select value={actionForm.operation} onChange={e => setActionForm({ ...actionForm, operation: e.target.value })}>
                  {SYMBOLIC_OPERATIONS.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input value={actionForm.rationale} onChange={e => setActionForm({ ...actionForm, rationale: e.target.value })} placeholder="optional rationale" />
              </div>
            </div>
            <button onClick={handlePerformAction} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Perform Action</button>
          </div>

          {/* Symbols List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Symbols ({symbols.length})</h3>
            <button onClick={() => loadSymbols()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {symbols.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No symbols registered. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {symbols.slice(0, 30).map((s: any, i: number) => {
                  const id = s.symbol_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>symbol {id}{s.content ? ` · ${s.content}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.symbol_type && renderBadge(s.symbol_type, themeColors.secondary)}
                          {s.density && renderBadge(s.density, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Actions List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Actions ({actions.length})</h3>
            <button onClick={() => loadActions()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {actions.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No actions performed. Perform one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {actions.slice(0, 30).map((a: any, i: number) => {
                  const id = a.action_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>action {id}{a.symbol_id ? ` · symbol: ${a.symbol_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.operation && renderBadge(a.operation, themeColors.secondary)}
                        </div>
                      </div>
                      {a.rationale && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{a.rationale}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Trace Section */}
      {activeSection === 'trace' && (
        <div className="dashboard-section">
          {/* Attempt Encoding */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Attempt Encoding</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={encodingForm.agent_id} onChange={e => setEncodingForm({ ...encodingForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Symbol ID</label>
                <input value={encodingForm.symbol_id} onChange={e => setEncodingForm({ ...encodingForm, symbol_id: e.target.value })} placeholder="optional symbol id" />
              </div>
              <div className="form-group">
                <label>Outcome</label>
                <select value={encodingForm.outcome} onChange={e => setEncodingForm({ ...encodingForm, outcome: e.target.value })}>
                  {ENCODING_OUTCOMES.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Target</label>
                <input value={encodingForm.target} onChange={e => setEncodingForm({ ...encodingForm, target: e.target.value })} placeholder="optional encoding target" />
              </div>
            </div>
            <button onClick={handleAttemptEncoding} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Attempt Encoding</button>
          </div>

          {/* Trace Transformation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Trace Transformation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={traceForm.agent_id} onChange={e => setTraceForm({ ...traceForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Symbol ID</label>
                <input value={traceForm.symbol_id} onChange={e => setTraceForm({ ...traceForm, symbol_id: e.target.value })} placeholder="optional symbol id" />
              </div>
              <div className="form-group">
                <label>Regime</label>
                <select value={traceForm.regime} onChange={e => setTraceForm({ ...traceForm, regime: e.target.value })}>
                  {TRANSFORMATION_REGIMES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Velocity</label>
                <input value={traceForm.velocity} onChange={e => setTraceForm({ ...traceForm, velocity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
            </div>
            <button onClick={handleTraceTransformation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Trace Transformation</button>
            {traceResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(traceResult, null, 2)}</pre>
            )}
          </div>

          {/* Encodings List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Encodings ({encodings.length})</h3>
            <button onClick={() => loadEncodings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {encodings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No encodings attempted. Attempt one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {encodings.slice(0, 30).map((e: any, i: number) => {
                  const id = e.encoding_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>encoding {id}{e.symbol_id ? ` · symbol: ${e.symbol_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.target && renderBadge(e.target, themeColors.secondary)}
                          {e.outcome && renderBadge(e.outcome, statusColor(e.outcome))}
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

export default CognitiveSymbologyPanel;
