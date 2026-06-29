import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#7c3aed',
  secondary: '#c4b5fd',
  bg: '#f5f3ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

const SOURCES = [
  'memory', 'knowledge_graph', 'web_search', 'document',
  'conversation_history', 'user_profile', 'agent_state',
  'external_api', 'tool_cache', 'semantic_cache', 'workspace',
  'skill_registry', 'embedding_index',
];
const ASSEMBLY_MODES = ['greedy', 'balanced', 'conservative', 'adaptive'];
const STRATEGIES = ['expand', 'focus', 'disambiguate', 'summarize', 'translate', 'multiply', 'rank'];

export const ContextProviderPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'connector' | 'enrich' | 'classify'>('overview');

  // Lists
  const [connectors, setConnectors] = useState<any[]>([]);
  const [bundles, setBundles] = useState<any[]>([]);

  // Connector form
  const [connectorForm, setConnectorForm] = useState({
    source: 'memory',
    name: '',
    description: '',
    priority: 'NORMAL',
    max_tokens: '2000',
  });

  // Enrich form
  const [enrichForm, setEnrichForm] = useState({
    user_input: '',
    target_tokens: '4000',
    assembly_mode: 'balanced',
    strategies: '',
  });
  const [enrichResult, setEnrichResult] = useState<any>(null);

  // Classify form
  const [classifyForm, setClassifyForm] = useState({
    user_input: '',
  });
  const [classifyResult, setClassifyResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, c, b] = await Promise.all([
        api.contextProvider.stats(),
        api.contextProvider.listConnectors(),
        api.contextProvider.listBundles({ limit: 20 }),
      ]);
      setStats(s);
      setConnectors(c || []);
      setBundles(b || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load context provider data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRegisterConnector = async () => {
    if (!connectorForm.name.trim()) return;
    try {
      await api.contextProvider.registerConnector({
        ...connectorForm,
        max_tokens: Number(connectorForm.max_tokens) || 2000,
      });
      toast.success(`Connector "${connectorForm.name}" registered`);
      setConnectorForm({
        source: 'memory',
        name: '',
        description: '',
        priority: 'NORMAL',
        max_tokens: '2000',
      });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleUnregister = async (id: string) => {
    try {
      await api.contextProvider.unregisterConnector(id);
      toast.success('Connector unregistered');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleEnrich = async () => {
    if (!enrichForm.user_input.trim()) return;
    try {
      const result = await api.contextProvider.enrich({
        ...enrichForm,
        target_tokens: Number(enrichForm.target_tokens) || 4000,
        strategies: enrichForm.strategies.split(',').map(s => s.trim()).filter(Boolean),
      });
      setEnrichResult(result);
      toast.success('Context enriched');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleClassify = async () => {
    if (!classifyForm.user_input.trim()) return;
    try {
      const result = await api.contextProvider.classifyIntent({
        ...classifyForm,
      });
      setClassifyResult(result);
      toast.success('Intent classified');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="forge-panel" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
        <div className="panel-header">
          <h2>🧠 Context Provider</h2>
          <p className="panel-subtitle">Intelligent context enrichment for agents</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading context provider...</span></div>
      </div>
    );
  }

  return (
    <div className="forge-panel" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧠 Context Provider</h2>
        <p className="panel-subtitle">Intelligent context enrichment for agents</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'connector', 'enrich', 'classify'] as const).map(s => (
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

      {/* Overview */}
      {activeSection === 'overview' && (
        <div className="forge-section">
          <div className="forge-card" style={{ background: themeColors.bg, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Context Provider Overview</h3>
            <div className="forge-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="forge-stat" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Queries</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats?.total_queries ?? 0}</div>
              </div>
              <div className="forge-stat" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Bundles</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats?.total_bundles ?? 0}</div>
              </div>
              <div className="forge-stat" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Fragments</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats?.total_fragments ?? 0}</div>
              </div>
              <div className="forge-stat" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Assembly (ms)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats?.avg_assembly_time_ms ?? 0}</div>
              </div>
            </div>
          </div>

          <div className="forge-card" style={{ background: themeColors.bg, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Connectors</h3>
            {connectors.length === 0 ? (
              <p style={{ color: themeColors.text, opacity: 0.7 }}>No connectors registered.</p>
            ) : (
              <table className="forge-table" style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8 }}>
                <thead>
                  <tr>
                    {['Connector ID', 'Source', 'Name', 'Status', 'Priority', 'Invocations', 'Action'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '8px 10px', borderBottom: `2px solid ${themeColors.border}`, color: themeColors.text }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {connectors.map((c, i) => (
                    <tr key={c.connector_id ?? i}>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{c.connector_id ?? '-'}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{c.source ?? '-'}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{c.name ?? '-'}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>
                        <span style={{ padding: '2px 8px', borderRadius: 12, background: c.status === 'active' ? themeColors.accent : '#eee', color: themeColors.text, fontSize: '0.8rem' }}>{c.status ?? '-'}</span>
                      </td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{c.priority ?? '-'}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{c.invocation_count ?? 0}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}` }}>
                        <button
                          className="btn-sm"
                          style={{ background: themeColors.primary, color: '#fff', border: 'none', padding: '4px 10px', borderRadius: 4, cursor: 'pointer' }}
                          onClick={() => c.connector_id && handleUnregister(c.connector_id)}
                        >
                          Unregister
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="forge-card" style={{ background: themeColors.bg, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Bundles</h3>
            {bundles.length === 0 ? (
              <p style={{ color: themeColors.text, opacity: 0.7 }}>No bundles available.</p>
            ) : (
              <table className="forge-table" style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8 }}>
                <thead>
                  <tr>
                    {['Bundle ID', 'Query ID', 'Total Tokens', 'Fragment Count'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '8px 10px', borderBottom: `2px solid ${themeColors.border}`, color: themeColors.text }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bundles.map((b, i) => (
                    <tr key={b.bundle_id ?? i}>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{b.bundle_id ?? '-'}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{b.query_id ?? '-'}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{b.total_tokens ?? 0}</td>
                      <td style={{ padding: '8px 10px', borderBottom: `1px solid ${themeColors.border}`, color: themeColors.text }}>{b.fragment_count ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Connector */}
      {activeSection === 'connector' && (
        <div className="forge-section">
          <h3 style={{ color: themeColors.text }}>Register Connector</h3>
          <div className="forge-form" style={{ marginBottom: 16, padding: 16, background: themeColors.bg, border: `1px solid ${themeColors.border}`, borderRadius: 8 }}>
            <div className="form-row" style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ color: themeColors.text }}>Source</label>
                <select
                  className="forge-select"
                  value={connectorForm.source}
                  onChange={e => setConnectorForm(f => ({ ...f, source: e.target.value }))}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                >
                  {SOURCES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ color: themeColors.text }}>Name *</label>
                <input
                  className="forge-input"
                  type="text"
                  value={connectorForm.name}
                  onChange={e => setConnectorForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. user-memory"
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                />
              </div>
            </div>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label style={{ color: themeColors.text }}>Description</label>
              <textarea
                className="forge-input"
                rows={3}
                value={connectorForm.description}
                onChange={e => setConnectorForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe this connector..."
                style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
              />
            </div>
            <div className="form-row" style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ color: themeColors.text }}>Priority</label>
                <select
                  className="forge-select"
                  value={connectorForm.priority}
                  onChange={e => setConnectorForm(f => ({ ...f, priority: e.target.value }))}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                >
                  {['CRITICAL', 'HIGH', 'NORMAL', 'LOW', 'BACKGROUND'].map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ color: themeColors.text }}>Max Tokens</label>
                <input
                  className="forge-input"
                  type="number"
                  min="0"
                  value={connectorForm.max_tokens}
                  onChange={e => setConnectorForm(f => ({ ...f, max_tokens: e.target.value }))}
                  placeholder="e.g. 2000"
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                />
              </div>
            </div>
            <button
              className="forge-btn"
              style={{ background: themeColors.primary, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer' }}
              onClick={handleRegisterConnector}
              disabled={!connectorForm.name.trim()}
            >
              Register Connector
            </button>
          </div>
        </div>
      )}

      {/* Enrich */}
      {activeSection === 'enrich' && (
        <div className="forge-section">
          <h3 style={{ color: themeColors.text }}>Enrich Context</h3>
          <div className="forge-form" style={{ marginBottom: 16, padding: 16, background: themeColors.bg, border: `1px solid ${themeColors.border}`, borderRadius: 8 }}>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label style={{ color: themeColors.text }}>User Input *</label>
              <textarea
                className="forge-input"
                rows={4}
                value={enrichForm.user_input}
                onChange={e => setEnrichForm(f => ({ ...f, user_input: e.target.value }))}
                placeholder="Enter the user query to enrich..."
                style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
              />
            </div>
            <div className="form-row" style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ color: themeColors.text }}>Target Tokens</label>
                <input
                  className="forge-input"
                  type="number"
                  min="0"
                  value={enrichForm.target_tokens}
                  onChange={e => setEnrichForm(f => ({ ...f, target_tokens: e.target.value }))}
                  placeholder="e.g. 4000"
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label style={{ color: themeColors.text }}>Assembly Mode</label>
                <select
                  className="forge-select"
                  value={enrichForm.assembly_mode}
                  onChange={e => setEnrichForm(f => ({ ...f, assembly_mode: e.target.value }))}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                >
                  {ASSEMBLY_MODES.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label style={{ color: themeColors.text }}>Strategies (comma-separated)</label>
              <input
                className="forge-input"
                type="text"
                value={enrichForm.strategies}
                onChange={e => setEnrichForm(f => ({ ...f, strategies: e.target.value }))}
                placeholder={`e.g. ${STRATEGIES.slice(0, 3).join(', ')}`}
                style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
              />
              <small style={{ color: themeColors.text, opacity: 0.7 }}>Available: {STRATEGIES.join(', ')}</small>
            </div>
            <button
              className="forge-btn"
              style={{ background: themeColors.primary, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer' }}
              onClick={handleEnrich}
              disabled={!enrichForm.user_input.trim()}
            >
              Enrich
            </button>
          </div>

          {enrichResult && (
            <div className="forge-card" style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Enrichment Result</h4>
              <div className="forge-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, marginTop: 12 }}>
                <div className="forge-stat" style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, fontSize: '0.85rem' }}>Bundle ID</div>
                  <div style={{ color: themeColors.primary, fontWeight: 700 }}>{enrichResult.bundle_id ?? '-'}</div>
                </div>
                <div className="forge-stat" style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, fontSize: '0.85rem' }}>Total Tokens</div>
                  <div style={{ color: themeColors.primary, fontWeight: 700 }}>{enrichResult.total_tokens ?? 0}</div>
                </div>
                <div className="forge-stat" style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, fontSize: '0.85rem' }}>Fragment Count</div>
                  <div style={{ color: themeColors.primary, fontWeight: 700 }}>{enrichResult.fragment_count ?? 0}</div>
                </div>
                <div className="forge-stat" style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, fontSize: '0.85rem' }}>Intent</div>
                  <div style={{ color: themeColors.primary, fontWeight: 700 }}>{enrichResult.intent ?? '-'}</div>
                </div>
                <div className="forge-stat" style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, fontSize: '0.85rem' }}>Assembly (ms)</div>
                  <div style={{ color: themeColors.primary, fontWeight: 700 }}>{enrichResult.assembly_time_ms ?? 0}</div>
                </div>
                <div className="forge-stat" style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, fontSize: '0.85rem' }}>Disambiguations</div>
                  <div style={{ color: themeColors.primary, fontWeight: 700 }}>{Array.isArray(enrichResult.disambiguations) ? enrichResult.disambiguations.length : 0}</div>
                </div>
              </div>
              {enrichResult.assembled_text && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 4 }}>Assembled Text (first 500 chars)</div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text, padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                    {typeof enrichResult.assembled_text === 'string' ? enrichResult.assembled_text.slice(0, 500) : JSON.stringify(enrichResult.assembled_text).slice(0, 500)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Classify */}
      {activeSection === 'classify' && (
        <div className="forge-section">
          <h3 style={{ color: themeColors.text }}>Classify Intent</h3>
          <div className="forge-form" style={{ marginBottom: 16, padding: 16, background: themeColors.bg, border: `1px solid ${themeColors.border}`, borderRadius: 8 }}>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label style={{ color: themeColors.text }}>User Input *</label>
              <textarea
                className="forge-input"
                rows={4}
                value={classifyForm.user_input}
                onChange={e => setClassifyForm(f => ({ ...f, user_input: e.target.value }))}
                placeholder="Enter the user query to classify..."
                style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
              />
            </div>
            <button
              className="forge-btn"
              style={{ background: themeColors.primary, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: 'pointer' }}
              onClick={handleClassify}
              disabled={!classifyForm.user_input.trim()}
            >
              Classify
            </button>
          </div>

          {classifyResult && (
            <div className="forge-card" style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Classification Result</h4>
              <div style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 8 }}>Intent</div>
                <div style={{ display: 'inline-block', padding: '8px 16px', borderRadius: 8, background: themeColors.primary, color: '#fff', fontWeight: 700 }}>
                  {classifyResult.intent ?? 'unknown'}
                </div>
              </div>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text, marginTop: 12, padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                {JSON.stringify(classifyResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ContextProviderPanel;
