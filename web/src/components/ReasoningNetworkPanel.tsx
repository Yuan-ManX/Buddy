import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#7c3aed',
  secondary: '#a78bfa',
  bg: '#f5f3ff',
  border: '#c4b5fd',
  accent: '#ede9fe',
  text: '#4c1d95',
};

const AVAILABLE_STRATEGIES = [
  'linear', 'branching', 'recursive', 'contrastive',
  'abductive', 'deductive', 'inductive', 'analogical',
];

export const ReasoningNetworkPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reason' | 'results'>('overview');

  const [reasonForm, setReasonForm] = useState({
    question: '', strategies: ['linear'] as string[], initial_context: '',
  });
  const [reasoning, setReasoning] = useState(false);
  const [results, setResults] = useState<any[] | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.reasoningNetwork.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load reasoning network data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleReason = async () => {
    if (!reasonForm.question.trim()) return;
    try {
      setReasoning(true);
      const result = await api.reasoningNetwork.reason({
        question: reasonForm.question,
        strategies: reasonForm.strategies.length > 0 ? reasonForm.strategies : undefined,
        initial_context: reasonForm.initial_context || undefined,
      });
      toast.success(`Reasoning complete — confidence: ${(result.confidence * 100).toFixed(1)}%`);
      setReasonForm({ question: '', strategies: ['linear'], initial_context: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
    finally { setReasoning(false); }
  };

  const handleLoadResults = async () => {
    try {
      const r = await api.reasoningNetwork.results(10);
      setResults(r.results || r);
    } catch (e: any) { toast.error(e.message); }
  };

  const toggleStrategy = (s: string) => {
    setReasonForm(f => ({
      ...f,
      strategies: f.strategies.includes(s)
        ? f.strategies.filter(x => x !== s)
        : [...f.strategies, s],
    }));
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🧠 Agentic Reasoning Network</h2>
          <p className="panel-subtitle">Multi-path reasoning and synthesis engine</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading reasoning network...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧠 Agentic Reasoning Network</h2>
        <p className="panel-subtitle">Multi-path reasoning and synthesis engine</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_queries ?? '-'}</span><span className="stat-label">Total Queries</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_paths_explored ?? '-'}</span><span className="stat-label">Paths Explored</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.avg_confidence?.toFixed?.(2) ?? stats.avg_confidence ?? '-'}</span><span className="stat-label">Avg Confidence</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.active_nodes ?? '-'}</span><span className="stat-label">Active Nodes</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reason', 'results'] as const).map(s => (
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
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Reasoning Network Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Results</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_results ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Paths</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.active_paths ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Execution</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_execution_ms?.toFixed?.(0) ?? '-'}ms</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Prune Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.path_prune_rate != null ? `${(stats.path_prune_rate * 100).toFixed(1)}%` : '-'}</div>
              </div>
            </div>
          </div>
          {stats.strategy_usage && Object.keys(stats.strategy_usage).length > 0 && (
            <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8 }}>
              <h4 style={{ color: themeColors.text }}>Strategy Usage</h4>
              {Object.entries(stats.strategy_usage).map(([strategy, count]: [string, any]) => (
                <div key={strategy} className="dashboard-stat-row">
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{strategy}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reason */}
      {activeSection === 'reason' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Execute Reasoning</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Question</label>
              <textarea
                rows={3}
                value={reasonForm.question}
                onChange={e => setReasonForm(f => ({ ...f, question: e.target.value }))}
                placeholder="Enter the question to reason about..."
              />
            </div>
            <div className="form-group">
              <label>Initial Context (optional)</label>
              <input
                type="text"
                value={reasonForm.initial_context}
                onChange={e => setReasonForm(f => ({ ...f, initial_context: e.target.value }))}
                placeholder="Additional context for reasoning..."
              />
            </div>
            <div className="form-group">
              <label>Strategies</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
                {AVAILABLE_STRATEGIES.map(s => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleStrategy(s)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 20,
                      border: `1px solid ${themeColors.border}`,
                      background: reasonForm.strategies.includes(s) ? themeColors.primary : '#fff',
                      color: reasonForm.strategies.includes(s) ? '#fff' : themeColors.text,
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      fontWeight: 500,
                      transition: 'all 0.2s',
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleReason}
              disabled={reasoning || !reasonForm.question.trim()}
            >
              {reasoning ? 'Reasoning...' : '🚀 Execute Reasoning'}
            </button>
          </div>
        </div>
      )}

      {/* Results */}
      {activeSection === 'results' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Results</h3>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleLoadResults}>Load Results</button>
          </div>
          {results ? (
            results.length === 0 ? (
              <div className="panel-empty">No reasoning results yet</div>
            ) : (
              <div className="forge-skill-list">
                {results.map((r: any, idx: number) => (
                  <div key={r.result_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                    <div className="forge-skill-header">
                      <div className="forge-skill-name" style={{ color: themeColors.text }}>{r.question}</div>
                      <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                        {(r.confidence * 100).toFixed?.(0) ?? r.confidence}%
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      <div style={{ color: themeColors.text, marginBottom: 4 }}>{r.conclusion?.slice(0, 200)}</div>
                      <div>Paths: {r.paths_explored} explored / {r.paths_selected} selected | {r.execution_time_ms?.toFixed?.(0)}ms</div>
                      {r.strategies_used?.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          {r.strategies_used.map((s: string) => (
                            <span key={s} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{s}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="panel-empty">Click "Load Results" to view recent reasoning results</div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReasoningNetworkPanel;