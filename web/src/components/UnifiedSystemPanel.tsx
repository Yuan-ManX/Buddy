import React, { useState, useEffect, useCallback } from 'react';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

interface UnifiedSystemStats {
  total_executions: number;
  total_tokens: number;
  active_sessions: number;
  total_insights: number;
  strategy_performance: Record<string, { success_rate: number; total_uses: number }>;
  capability_registry: Record<string, string[]>;
}

interface Insight {
  insight_id: string;
  category: string;
  description: string;
  severity: string;
  action_items: string[];
  timestamp: string;
}

interface CycleResult {
  session_id: string;
  mode: string;
  success: boolean;
  content: string;
  error: string;
  latency_ms: number;
  metadata: Record<string, unknown>;
  insights: Insight[];
}

export const UnifiedSystemPanel: React.FC = () => {
  const [stats, setStats] = useState<UnifiedSystemStats | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testContent, setTestContent] = useState('');
  const [testMode, setTestMode] = useState('reactive');
  const [testResult, setTestResult] = useState<CycleResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'test' | 'insights'>('overview');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, insightsRes] = await Promise.all([
        request<UnifiedSystemStats>('/api/unified-system/stats'),
        request<{ insights: Insight[] }>('/api/unified-system/insights?limit=20'),
      ]);
      setStats(statsRes);
      setInsights(insightsRes.insights || []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunTest = async () => {
    if (!testContent.trim()) return;
    try {
      setTestLoading(true);
      const result = await request<CycleResult>('/api/unified-system/run', {
        method: 'POST',
        body: JSON.stringify({
          content: testContent,
          mode: testMode,
          enable_tools: false,
          enable_reasoning: true,
          enable_reflection: true,
        }),
      });
      setTestResult(result);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Test failed');
    } finally {
      setTestLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Unified Agent System</h2>
        </div>
        <div className="panel-body" style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
          <div className="loading-spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Unified Agent System</h2>
        <span className="panel-badge" style={{ background: stats ? '#22c55e' : '#ef4444' }}>
          {stats ? 'Active' : 'Offline'}
        </span>
      </div>

      {error && (
        <div className="error-banner" style={{ background: '#fef2f2', color: '#dc2626', padding: '12px', margin: '0 16px', borderRadius: '8px' }}>
          {error}
        </div>
      )}

      <div className="tab-bar" style={{ display: 'flex', gap: '8px', padding: '16px', borderBottom: '1px solid #e5e7eb' }}>
        {(['overview', 'test', 'insights'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              background: activeTab === tab ? '#3b82f6' : '#f3f4f6',
              color: activeTab === tab ? '#fff' : '#374151',
              fontSize: '13px',
              fontWeight: 500,
            }}
          >
            {tab === 'overview' ? 'Overview' : tab === 'test' ? 'Test Cycle' : 'Insights'}
          </button>
        ))}
      </div>

      <div className="panel-body" style={{ padding: '16px' }}>
        {activeTab === 'overview' && stats && (
          <div>
            {/* Cognitive Cycle Visualization */}
            <div className="section" style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>Cognitive Cycle</h3>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: '12px',
                overflow: 'hidden',
              }}>
                {['Perceive', 'Understand', 'Reason', 'Plan', 'Execute', 'Reflect'].map((phase, i) => (
                  <React.Fragment key={phase}>
                    <div style={{ textAlign: 'center', color: '#fff', flex: 1 }}>
                      <div style={{
                        width: '40px', height: '40px',
                        borderRadius: '50%',
                        background: 'rgba(255,255,255,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        margin: '0 auto 4px',
                        fontSize: '16px',
                      }}>
                        {i + 1}
                      </div>
                      <div style={{ fontSize: '11px', fontWeight: 500 }}>{phase}</div>
                    </div>
                    {i < 5 && (
                      <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '18px' }}>→</div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginBottom: '24px' }}>
              <div className="stat-card" style={statCardStyle}>
                <div className="stat-value" style={{ fontSize: '28px', fontWeight: 700, color: '#3b82f6' }}>{stats.total_executions}</div>
                <div className="stat-label" style={{ fontSize: '12px', color: '#6b7280' }}>Total Executions</div>
              </div>
              <div className="stat-card" style={statCardStyle}>
                <div className="stat-value" style={{ fontSize: '28px', fontWeight: 700, color: '#8b5cf6' }}>{stats.active_sessions}</div>
                <div className="stat-label" style={{ fontSize: '12px', color: '#6b7280' }}>Active Sessions</div>
              </div>
              <div className="stat-card" style={statCardStyle}>
                <div className="stat-value" style={{ fontSize: '28px', fontWeight: 700, color: '#22c55e' }}>{stats.total_insights}</div>
                <div className="stat-label" style={{ fontSize: '12px', color: '#6b7280' }}>Total Insights</div>
              </div>
              <div className="stat-card" style={statCardStyle}>
                <div className="stat-value" style={{ fontSize: '28px', fontWeight: 700, color: '#f59e0b' }}>{stats.total_tokens}</div>
                <div className="stat-label" style={{ fontSize: '12px', color: '#6b7280' }}>Tokens Used</div>
              </div>
            </div>

            {/* Strategy Performance */}
            {Object.keys(stats.strategy_performance).length > 0 && (
              <div className="section" style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>Strategy Performance</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {Object.entries(stats.strategy_performance).map(([strategy, perf]) => (
                    <div key={strategy} style={{
                      display: 'flex', alignItems: 'center', gap: '12px',
                      padding: '10px 12px', background: '#f9fafb', borderRadius: '8px',
                    }}>
                      <span style={{ flex: 1, fontSize: '13px', fontWeight: 500, textTransform: 'capitalize' }}>
                        {strategy.replace(/_/g, ' ')}
                      </span>
                      <div style={{
                        width: '120px', height: '6px', background: '#e5e7eb', borderRadius: '3px',
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          width: `${(perf.success_rate * 100).toFixed(0)}%`,
                          height: '100%',
                          background: perf.success_rate > 0.7 ? '#22c55e' : perf.success_rate > 0.4 ? '#f59e0b' : '#ef4444',
                          borderRadius: '3px',
                          transition: 'width 0.3s ease',
                        }} />
                      </div>
                      <span style={{ fontSize: '12px', color: '#6b7280', minWidth: '80px', textAlign: 'right' }}>
                        {(perf.success_rate * 100).toFixed(0)}% ({perf.total_uses} uses)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'test' && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#374151' }}>
                Test Content
              </label>
              <textarea
                value={testContent}
                onChange={(e) => setTestContent(e.target.value)}
                placeholder="Enter a task or question to test the unified agent cognitive cycle..."
                rows={4}
                style={{
                  width: '100%', padding: '12px',
                  border: '1px solid #d1d5db', borderRadius: '8px',
                  fontSize: '13px', resize: 'vertical',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#374151' }}>
                System Mode
              </label>
              <select
                value={testMode}
                onChange={(e) => setTestMode(e.target.value)}
                style={{
                  width: '100%', padding: '8px 12px',
                  border: '1px solid #d1d5db', borderRadius: '8px',
                  fontSize: '13px', background: '#fff',
                }}
              >
                <option value="reactive">Reactive - Direct Response</option>
                <option value="deliberative">Deliberative - Think Before Acting</option>
                <option value="autonomous">Autonomous - Self-Directed</option>
                <option value="exploratory">Exploratory - Open Discovery</option>
              </select>
            </div>

            <button
              onClick={handleRunTest}
              disabled={testLoading || !testContent.trim()}
              style={{
                width: '100%', padding: '12px',
                background: testLoading || !testContent.trim() ? '#9ca3af' : '#3b82f6',
                color: '#fff', border: 'none', borderRadius: '8px',
                fontSize: '14px', fontWeight: 600, cursor: 'pointer',
              }}
            >
              {testLoading ? 'Running cognitive cycle...' : 'Run Unified Cycle'}
            </button>

            {testResult && (
              <div style={{ marginTop: '16px' }}>
                <div style={{
                  padding: '12px', borderRadius: '8px',
                  background: testResult.success ? '#f0fdf4' : '#fef2f2',
                  border: `1px solid ${testResult.success ? '#bbf7d0' : '#fecaca'}`,
                  marginBottom: '12px',
                }}>
                  <div style={{ fontWeight: 600, fontSize: '14px', color: testResult.success ? '#166534' : '#991b1b' }}>
                    {testResult.success ? 'Cycle Completed Successfully' : 'Cycle Failed'}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                    Session: {testResult.session_id} | Mode: {testResult.mode} | Latency: {testResult.latency_ms.toFixed(0)}ms
                  </div>
                </div>

                {testResult.content && (
                  <div style={{
                    padding: '12px', background: '#f9fafb', borderRadius: '8px',
                    fontSize: '13px', lineHeight: '1.5', whiteSpace: 'pre-wrap',
                    marginBottom: '12px',
                  }}>
                    {testResult.content}
                  </div>
                )}

                {testResult.metadata && (
                  <div style={{ marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '13px', color: '#374151', marginBottom: '8px' }}>Metadata</h4>
                    <div style={{
                      display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px',
                    }}>
                      {Object.entries(testResult.metadata).map(([key, value]) => (
                        <div key={key} style={{ padding: '8px', background: '#f9fafb', borderRadius: '6px' }}>
                          <div style={{ fontSize: '11px', color: '#6b7280', textTransform: 'capitalize' }}>
                            {key.replace(/_/g, ' ')}
                          </div>
                          <div style={{ fontSize: '13px', fontWeight: 500 }}>
                            {Array.isArray(value) ? value.join(', ') : String(value)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {testResult.insights && testResult.insights.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: '13px', color: '#374151', marginBottom: '8px' }}>Insights</h4>
                    {testResult.insights.map((insight, i) => (
                      <div key={i} style={{
                        padding: '10px', marginBottom: '8px',
                        background: insight.severity === 'critical' ? '#fef2f2' : insight.severity === 'warning' ? '#fffbeb' : '#f0fdf4',
                        borderRadius: '8px', border: '1px solid #e5e7eb',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{
                            padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                            background: insight.severity === 'critical' ? '#fecaca' : insight.severity === 'warning' ? '#fde68a' : '#bbf7d0',
                            color: insight.severity === 'critical' ? '#991b1b' : insight.severity === 'warning' ? '#92400e' : '#166534',
                          }}>
                            {insight.severity}
                          </span>
                          <span style={{ fontSize: '11px', color: '#6b7280', textTransform: 'capitalize' }}>
                            {insight.category}
                          </span>
                        </div>
                        <div style={{ fontSize: '13px', color: '#374151' }}>{insight.description}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'insights' && (
          <div>
            {insights.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
                No insights generated yet. Run a cognitive cycle to generate insights.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {insights.map((insight) => (
                  <div key={insight.insight_id} style={{
                    padding: '12px', background: '#f9fafb', borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                        background: insight.severity === 'critical' ? '#fecaca' : insight.severity === 'warning' ? '#fde68a' : '#bbf7d0',
                        color: insight.severity === 'critical' ? '#991b1b' : insight.severity === 'warning' ? '#92400e' : '#166534',
                      }}>
                        {insight.severity}
                      </span>
                      <span style={{ fontSize: '11px', color: '#6b7280', textTransform: 'capitalize' }}>
                        {insight.category}
                      </span>
                      <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#9ca3af' }}>
                        {new Date(insight.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#374151', marginBottom: '6px' }}>
                      {insight.description}
                    </div>
                    {insight.action_items.length > 0 && (
                      <div style={{ fontSize: '12px', color: '#6b7280' }}>
                        Actions: {insight.action_items.join('; ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const statCardStyle: React.CSSProperties = {
  padding: '16px',
  background: '#f9fafb',
  borderRadius: '10px',
  border: '1px solid #e5e7eb',
  textAlign: 'center',
};