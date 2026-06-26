import React, { useState, useEffect, useCallback } from 'react';

const BASE_URL = '/api';
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try { const parsed = JSON.parse(body); message = parsed.detail || parsed.error || body; } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Tabs for the feedback orchestrator
type Tab = 'Overview' | 'Collect' | 'Analytics' | 'Rules';

export const FeedbackOrchestratorPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('Overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview tab state
  const [stats, setStats] = useState<any>(null);

  // Collect tab state
  const [collectForm, setCollectForm] = useState({
    source: 'user_feedback',
    severity: 'medium',
    confidence: 0.8,
    target: '',
    payload: '',
    session_id: '',
    agent_id: '',
  });
  const [collectResult, setCollectResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  // Analytics tab state
  const [analytics, setAnalytics] = useState<any>(null);
  const [analyticsWindow, setAnalyticsWindow] = useState(24);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Rules tab state
  const [rules, setRules] = useState<any[]>([]);
  const [newRule, setNewRule] = useState({ name: '', pattern: '', target: '', priority: 1 });
  const [rulesLoading, setRulesLoading] = useState(false);

  // Load overview stats
  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<any>('/feedback-orchestrator/stats');
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load analytics
  const loadAnalytics = useCallback(async () => {
    try {
      setAnalyticsLoading(true);
      const data = await request<any>(`/feedback-orchestrator/analytics?window_hours=${analyticsWindow}`);
      setAnalytics(data);
    } catch (err: any) {
      alert('Failed to load analytics: ' + err.message);
    } finally {
      setAnalyticsLoading(false);
    }
  }, [analyticsWindow]);

  // Load rules
  const loadRules = useCallback(async () => {
    try {
      setRulesLoading(true);
      const data = await request<any>('/feedback-orchestrator/routing-rules');
      setRules(data.rules || data || []);
    } catch (err: any) {
      alert('Failed to load rules: ' + err.message);
    } finally {
      setRulesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadRules();
  }, [loadStats, loadRules]);

  // Handle collect feedback
  const handleCollect = useCallback(async () => {
    if (!collectForm.payload.trim()) {
      alert('Payload is required');
      return;
    }
    try {
      setSubmitting(true);
      // Step 1: Collect feedback
      const feedback = await request<any>('/feedback-orchestrator/collect', {
        method: 'POST',
        body: JSON.stringify({
          source: collectForm.source,
          severity: collectForm.severity,
          confidence: collectForm.confidence,
          target: collectForm.target,
          payload: collectForm.payload,
          session_id: collectForm.session_id || undefined,
          agent_id: collectForm.agent_id || undefined,
        }),
      });

      // Step 2: Route the feedback
      const routeResult = await request<any>('/feedback-orchestrator/route', {
        method: 'POST',
        body: JSON.stringify({ feedback_id: feedback.feedback_id || feedback.id }),
      });

      // Step 3: Execute if routing succeeded
      let execResult: any = null;
      if (routeResult.routed) {
        execResult = await request<any>('/feedback-orchestrator/execute', {
          method: 'POST',
          body: JSON.stringify({ feedback_id: feedback.feedback_id || feedback.id }),
        });
      }

      setCollectResult({ feedback, route: routeResult, execution: execResult });
      setCollectForm({ ...collectForm, payload: '', target: '', session_id: '', agent_id: '' });
      loadStats();
    } catch (err: any) {
      alert('Collect failed: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  }, [collectForm, loadStats]);

  // Handle add rule
  const handleAddRule = useCallback(async () => {
    if (!newRule.name.trim() || !newRule.pattern.trim() || !newRule.target.trim()) {
      alert('Name, pattern, and target are required');
      return;
    }
    try {
      await request<any>('/feedback-orchestrator/routing-rules', {
        method: 'POST',
        body: JSON.stringify(newRule),
      });
      setNewRule({ name: '', pattern: '', target: '', priority: 1 });
      loadRules();
    } catch (err: any) {
      alert('Failed to add rule: ' + err.message);
    }
  }, [newRule, loadRules]);

  // Handle delete rule
  const handleDeleteRule = useCallback(async (ruleId: string) => {
    if (!confirm('Delete this routing rule?')) return;
    try {
      await request<any>(`/feedback-orchestrator/routing-rules/${ruleId}`, { method: 'DELETE' });
      loadRules();
    } catch (err: any) {
      alert('Failed to delete rule: ' + err.message);
    }
  }, [loadRules]);

  // Dark theme colors
  const colors = {
    bg: '#1a1a2e',
    card: '#16213e',
    border: '#2a2a4a',
    text: '#e0e0e0',
    accent: '#7c3aed',
    textSecondary: '#a0a0b0',
    green: '#10b981',
    red: '#ef4444',
    yellow: '#f59e0b',
    blue: '#3b82f6',
  };

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '8px 16px',
    border: 'none',
    borderRadius: '8px',
    background: activeTab === tab ? colors.accent : colors.card,
    color: activeTab === tab ? '#fff' : colors.textSecondary,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    transition: 'all 0.15s',
  });

  const inputStyle: React.CSSProperties = {
    padding: '8px 12px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    background: colors.bg,
    color: colors.text,
    fontSize: '14px',
    width: '100%',
    boxSizing: 'border-box',
  };

  const btnPrimary: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    background: colors.accent,
    color: '#fff',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  };

  const btnSecondary: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    background: colors.card,
    color: colors.text,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  };

  if (loading) {
    return (
      <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
        <div className="panel-header">
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Feedback Orchestrator</h2>
          <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>Collect, route, analyze, and manage feedback loops</p>
        </div>
        <div className="panel-loading" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <span style={{ color: colors.textSecondary }}>Loading feedback orchestrator data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Feedback Orchestrator</h2>
        <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>
          Collect, route, analyze, and manage feedback loops
        </p>
        {error && (
          <div className="error-banner" style={{ padding: '10px 16px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', color: colors.red, marginTop: '8px', fontSize: '14px' }}>
            {error}
            <button onClick={() => { setError(null); loadStats(); }} style={{ marginLeft: '8px', background: 'none', border: 'none', color: colors.red, cursor: 'pointer', fontWeight: 600 }}>Dismiss</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar" style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' as const }}>
          {[
            { label: 'Total Feedback', value: stats.total_feedback ?? stats.total ?? '0', color: colors.accent },
            { label: 'Routed', value: stats.routed ?? stats.routed_count ?? '0', color: colors.blue },
            { label: 'Pending', value: stats.pending ?? stats.pending_count ?? '0', color: colors.yellow },
            { label: 'Executed', value: stats.executed ?? stats.executed_count ?? '0', color: colors.green },
            { label: 'Rules', value: stats.total_rules ?? stats.rules_count ?? '0', color: colors.accent },
          ].map((stat) => (
            <div key={stat.label} className="stat-item" style={{
              flex: '1 1 120px', minWidth: '120px', background: colors.card,
              border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '14px 18px',
              display: 'flex', alignItems: 'center', gap: '12px',
            }}>
              <div className="stat-content" style={{ display: 'flex', flexDirection: 'column' }}>
                <span className="stat-value" style={{ fontSize: '1.3rem', fontWeight: 800, color: colors.text }}>{stat.value}</span>
                <span className="stat-label" style={{ fontSize: '0.72rem', color: colors.textSecondary, fontWeight: 600 }}>{stat.label}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {(['Overview', 'Collect', 'Analytics', 'Rules'] as Tab[]).map((tab) => (
          <button key={tab} className={`forge-tab ${activeTab === tab ? 'active' : ''}`}
            style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'Overview' && stats && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Overview</h3>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Total Feedback</span>
            <strong>{stats.total_feedback ?? stats.total ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Routed</span>
            <strong>{stats.routed ?? stats.routed_count ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Pending</span>
            <strong style={{ color: colors.yellow }}>{stats.pending ?? stats.pending_count ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Executed</span>
            <strong style={{ color: colors.green }}>{stats.executed ?? stats.executed_count ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Routing Rules</span>
            <strong>{stats.total_rules ?? stats.rules_count ?? 'N/A'}</strong>
          </div>
          {stats.sources && (
            <>
              <h3 style={{ margin: '20px 0 12px', fontSize: '14px', fontWeight: 600 }}>Feedback by Source</h3>
              {Object.entries(stats.sources).map(([source, count]: [string, any]) => (
                <div key={source} className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
                  <span style={{ color: colors.textSecondary, textTransform: 'capitalize' }}>{source.replace(/_/g, ' ')}</span>
                  <strong>{count}</strong>
                </div>
              ))}
            </>
          )}
          <div style={{ marginTop: '16px' }}>
            <button onClick={loadStats} style={btnSecondary}>Refresh Stats</button>
          </div>
        </div>
      )}

      {/* Collect Tab */}
      {activeTab === 'Collect' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Collect Feedback</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Source */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Source</label>
              <select value={collectForm.source} onChange={(e) => setCollectForm({ ...collectForm, source: e.target.value })}
                style={inputStyle}>
                <option value="user_feedback">User Feedback</option>
                <option value="agent_review">Agent Review</option>
                <option value="system_alert">System Alert</option>
                <option value="external_api">External API</option>
                <option value="manual">Manual</option>
              </select>
            </div>
            {/* Severity */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Severity</label>
              <select value={collectForm.severity} onChange={(e) => setCollectForm({ ...collectForm, severity: e.target.value })}
                style={inputStyle}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            {/* Confidence */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>
                Confidence: {collectForm.confidence.toFixed(2)}
              </label>
              <input type="range" min="0" max="1" step="0.05" value={collectForm.confidence}
                onChange={(e) => setCollectForm({ ...collectForm, confidence: parseFloat(e.target.value) })}
                style={{ width: '100%', accentColor: colors.accent }} />
            </div>
            {/* Target */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Target</label>
              <input type="text" value={collectForm.target}
                onChange={(e) => setCollectForm({ ...collectForm, target: e.target.value })}
                placeholder="e.g. agent-id, module-name" style={inputStyle} />
            </div>
            {/* Payload */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Payload</label>
              <textarea value={collectForm.payload}
                onChange={(e) => setCollectForm({ ...collectForm, payload: e.target.value })}
                placeholder='Enter feedback payload...'
                rows={3}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }} />
            </div>
            {/* Session ID & Agent ID */}
            <div style={{ display: 'flex', gap: '12px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Session ID</label>
                <input type="text" value={collectForm.session_id}
                  onChange={(e) => setCollectForm({ ...collectForm, session_id: e.target.value })}
                  placeholder="Optional" style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: colors.textSecondary, marginBottom: '4px' }}>Agent ID</label>
                <input type="text" value={collectForm.agent_id}
                  onChange={(e) => setCollectForm({ ...collectForm, agent_id: e.target.value })}
                  placeholder="Optional" style={inputStyle} />
              </div>
            </div>
            {/* Submit */}
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button onClick={handleCollect} disabled={submitting} style={{
                ...btnPrimary, opacity: submitting ? 0.6 : 1, cursor: submitting ? 'not-allowed' : 'pointer',
              }}>
                {submitting ? 'Submitting...' : 'Collect & Route'}
              </button>
            </div>
          </div>
          {/* Result */}
          {collectResult && (
            <div style={{ marginTop: '16px', padding: '12px', background: colors.bg, borderRadius: '8px', border: `1px solid ${colors.border}` }}>
              <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600, color: colors.green }}>Result</h4>
              <pre style={{ fontSize: '12px', color: colors.text, whiteSpace: 'pre-wrap', margin: 0, overflow: 'auto', maxHeight: '200px' }}>
                {JSON.stringify(collectResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'Analytics' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Analytics</h3>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
            <label style={{ fontSize: '13px', fontWeight: 600, color: colors.textSecondary }}>Window (hours):</label>
            <input type="number" value={analyticsWindow} min={1} max={720}
              onChange={(e) => setAnalyticsWindow(parseInt(e.target.value) || 24)}
              style={{ ...inputStyle, width: '100px' }} />
            <button onClick={loadAnalytics} disabled={analyticsLoading} style={btnPrimary}>
              {analyticsLoading ? 'Loading...' : 'Load'}
            </button>
          </div>
          {analytics ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                {[
                  { label: 'Total', value: analytics.total ?? analytics.total_feedback ?? '0', color: colors.accent },
                  { label: 'Avg Confidence', value: analytics.avg_confidence ? (analytics.avg_confidence * 100).toFixed(1) + '%' : 'N/A', color: colors.blue },
                  { label: 'Avg Response Time', value: analytics.avg_response_time ? analytics.avg_response_time + 'ms' : 'N/A', color: colors.green },
                  { label: 'Resolution Rate', value: analytics.resolution_rate ? (analytics.resolution_rate * 100).toFixed(1) + '%' : 'N/A', color: colors.yellow },
                ].map((item) => (
                  <div key={item.label} style={{ background: colors.bg, borderRadius: '8px', padding: '12px', textAlign: 'center', border: `1px solid ${colors.border}` }}>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: item.color }}>{item.value}</div>
                    <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '4px' }}>{item.label}</div>
                  </div>
                ))}
              </div>
              {analytics.source_distribution && (
                <>
                  <h4 style={{ margin: '16px 0 8px', fontSize: '14px', fontWeight: 600 }}>Source Distribution</h4>
                  {Object.entries(analytics.source_distribution).map(([source, count]: [string, any]) => (
                    <div key={source} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${colors.border}`, fontSize: '13px' }}>
                      <span style={{ color: colors.textSecondary, textTransform: 'capitalize' }}>{source.replace(/_/g, ' ')}</span>
                      <strong>{count}</strong>
                    </div>
                  ))}
                </>
              )}
              {analytics.severity_distribution && (
                <>
                  <h4 style={{ margin: '16px 0 8px', fontSize: '14px', fontWeight: 600 }}>Severity Distribution</h4>
                  {Object.entries(analytics.severity_distribution).map(([severity, count]: [string, any]) => (
                    <div key={severity} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${colors.border}`, fontSize: '13px' }}>
                      <span style={{ color: colors.textSecondary, textTransform: 'capitalize' }}>{severity}</span>
                      <strong>{count}</strong>
                    </div>
                  ))}
                </>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
              {analyticsLoading ? 'Loading analytics...' : 'Click "Load" to fetch analytics data'}
            </div>
          )}
        </div>
      )}

      {/* Rules Tab */}
      {activeTab === 'Rules' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Routing Rules</h3>

          {/* Add new rule */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Add New Rule</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input type="text" value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  placeholder="Rule name" style={{ ...inputStyle, flex: 1 }} />
                <input type="number" value={newRule.priority} min={1} max={10}
                  onChange={(e) => setNewRule({ ...newRule, priority: parseInt(e.target.value) || 1 })}
                  placeholder="Priority" style={{ ...inputStyle, width: '80px' }} />
              </div>
              <input type="text" value={newRule.pattern}
                onChange={(e) => setNewRule({ ...newRule, pattern: e.target.value })}
                placeholder="Pattern (e.g. source=user_feedback)" style={inputStyle} />
              <input type="text" value={newRule.target}
                onChange={(e) => setNewRule({ ...newRule, target: e.target.value })}
                placeholder="Target (e.g. agent-id, module)" style={inputStyle} />
              <button onClick={handleAddRule} style={btnPrimary}>Add Rule</button>
            </div>
          </div>

          {/* Rules list */}
          <div style={{ marginTop: '16px' }}>
            {rules.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {rulesLoading ? 'Loading rules...' : 'No routing rules configured yet'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {rules.map((rule: any, idx: number) => (
                  <div key={rule.id || rule.rule_id || idx} className="forge-skill-card"
                    style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                      border: `1px solid ${colors.border}`,
                    }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>{rule.name || rule.pattern}</div>
                      <div style={{ fontSize: '12px', color: colors.textSecondary, marginTop: '2px' }}>
                        Pattern: {rule.pattern} → Target: {rule.target}
                      </div>
                      <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '2px' }}>
                        Priority: {rule.priority ?? 'N/A'}
                      </div>
                    </div>
                    <button onClick={() => handleDeleteRule(rule.id || rule.rule_id)}
                      style={{ ...btnSecondary, color: colors.red, borderColor: colors.red, fontSize: '12px', padding: '4px 12px' }}>
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};