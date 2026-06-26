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

interface AnalyticsStats {
  total_metrics: number;
  total_insights: number;
  total_data_points: number;
  agents_tracked: number;
  dashboards: number;
}

interface DashboardData {
  id: string;
  name: string;
  panels: DashboardPanel[];
  updated_at: string;
}

interface DashboardPanel {
  id: string;
  title: string;
  type: string;
  metric: string;
  value: number;
  trend: number;
  unit: string;
}

interface Metric {
  id: string;
  name: string;
  description: string;
  category: string;
  current_value: number;
  previous_value: number;
  change_percent: number;
  unit: string;
  updated_at: string;
}

interface AgentPerformance {
  agent_id: string;
  agent_name: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  avg_duration_ms: number;
  success_rate: number;
  efficiency_score: number;
  tokens_used: number;
  cost: number;
}

interface Insight {
  id: string;
  title: string;
  description: string;
  severity: string;
  category: string;
  agent_id: string;
  metric: string;
  recommendation: string;
  created_at: string;
}

interface SummaryData {
  total_agents: number;
  total_tasks: number;
  overall_success_rate: number;
  total_tokens: number;
  total_cost: number;
  period: string;
}

type Tab = 'summary' | 'dashboard' | 'metrics' | 'performance' | 'insights';

export const AnalyticsEnginePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Stats
  const [stats, setStats] = useState<AnalyticsStats | null>(null);

  // Summary
  const [summary, setSummary] = useState<SummaryData | null>(null);

  // Dashboard
  const [dashboards, setDashboards] = useState<DashboardData[]>([]);
  const [selectedDashboard, setSelectedDashboard] = useState<string>('');

  // Metrics
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [metricCategory, setMetricCategory] = useState('');
  const [metricSearch, setMetricSearch] = useState('');
  const [selectedMetric, setSelectedMetric] = useState<Metric | null>(null);

  // Performance
  const [performances, setPerformances] = useState<AgentPerformance[]>([]);
  const [perfSortBy, setPerfSortBy] = useState<'success_rate' | 'efficiency_score' | 'tasks'>('success_rate');

  // Insights
  const [insights, setInsights] = useState<Insight[]>([]);
  const [insightSeverity, setInsightSeverity] = useState('');
  const [insightPage, setInsightPage] = useState(1);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<AnalyticsStats>('/analytics-engine/stats');
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load analytics stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSummary = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<SummaryData>('/analytics-engine/summary');
      setSummary(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load summary');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<{ dashboards: DashboardData[] }>('/analytics-engine/dashboard');
      setDashboards(data.dashboards || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMetrics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (metricCategory) params.set('category', metricCategory);
      if (metricSearch) params.set('search', metricSearch);
      const data = await request<{ metrics: Metric[] }>(`/analytics-engine/metrics?${params.toString()}`);
      setMetrics(data.metrics || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  }, [metricCategory, metricSearch]);

  const loadPerformance = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set('sort_by', perfSortBy);
      const data = await request<{ agents: AgentPerformance[] }>(`/analytics-engine/performance?${params.toString()}`);
      setPerformances(data.agents || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load performance data');
    } finally {
      setLoading(false);
    }
  }, [perfSortBy]);

  const loadInsights = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set('page', String(insightPage));
      params.set('page_size', '20');
      if (insightSeverity) params.set('severity', insightSeverity);
      const data = await request<{ insights: Insight[]; total: number }>(`/analytics-engine/insights?${params.toString()}`);
      setInsights(data.insights || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load insights');
    } finally {
      setLoading(false);
    }
  }, [insightPage, insightSeverity]);

  useEffect(() => {
    loadStats();
    loadSummary();
  }, []);

  const severityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#dc2626';
      case 'high': return '#ea580c';
      case 'medium': return '#f59e0b';
      case 'low': return '#3b82f6';
      case 'info': return '#6b7280';
      default: return '#9ca3af';
    }
  };

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '8px 16px',
    background: activeTab === tab ? '#3b82f6' : '#f3f4f6',
    color: activeTab === tab ? '#fff' : '#374151',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontWeight: activeTab === tab ? 600 : 400,
    fontSize: 13,
  });

  const statCardStyle: React.CSSProperties = {
    flex: 1,
    background: '#f9fafb',
    borderRadius: 12,
    padding: 16,
    textAlign: 'center',
    border: '1px solid #e5e7eb',
  };

  if (loading && !stats && !summary) {
    return <div style={{ padding: 24, color: '#6b7280' }}>Loading analytics engine data...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Analytics Engine</h2>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0', fontSize: 13 }}>Metrics, dashboards, agent performance, and insights</p>
        </div>
        <button
          onClick={() => { loadStats(); loadSummary(); }}
          style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: '#fef2f2', borderRadius: 8, color: '#dc2626', marginBottom: 16, fontSize: 13 }}>
          {error}
          <button style={{ marginLeft: 12, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_metrics}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Metrics</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.total_insights}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Insights</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#059669' }}>{stats.total_data_points.toLocaleString()}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Data Points</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#ea580c' }}>{stats.agents_tracked}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Agents Tracked</div>
          </div>
          <div style={statCardStyle}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#dc2626' }}>{stats.dashboards}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Dashboards</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        {(['summary', 'dashboard', 'metrics', 'performance', 'insights'] as Tab[]).map(tab => (
          <button key={tab} style={tabStyle(tab)} onClick={() => {
            setActiveTab(tab);
            if (tab === 'dashboard') loadDashboard();
            if (tab === 'metrics') loadMetrics();
            if (tab === 'performance') loadPerformance();
            if (tab === 'insights') loadInsights();
          }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Summary Tab */}
      {activeTab === 'summary' && summary && (
        <div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{summary.total_agents}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Agents</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{summary.total_tasks.toLocaleString()}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Tasks</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: summary.overall_success_rate >= 90 ? '#10b981' : '#f59e0b' }}>
                {summary.overall_success_rate.toFixed(1)}%
              </div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Success Rate</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#059669' }}>{summary.total_tokens.toLocaleString()}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Tokens</div>
            </div>
            <div style={statCardStyle}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ea580c' }}>${summary.total_cost.toFixed(4)}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>Total Cost</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0' }}>Period Overview</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Period</span>
                  <span style={{ fontWeight: 600 }}>{summary.period}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Avg Tasks / Agent</span>
                  <span style={{ fontWeight: 600 }}>
                    {summary.total_agents > 0 ? (summary.total_tasks / summary.total_agents).toFixed(1) : '0'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Avg Tokens / Task</span>
                  <span style={{ fontWeight: 600 }}>
                    {summary.total_tasks > 0 ? (summary.total_tokens / summary.total_tasks).toFixed(0) : '0'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Avg Cost / Task</span>
                  <span style={{ fontWeight: 600 }}>
                    {summary.total_tasks > 0 ? `$${(summary.total_cost / summary.total_tasks).toFixed(6)}` : '$0'}
                  </span>
                </div>
              </div>
            </div>
            <div style={{ flex: 2, background: '#f9fafb', borderRadius: 12, padding: 16, border: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px 0', width: '100%' }}>Success Rate</h3>
              <div style={{ position: 'relative', width: 120, height: 120 }}>
                <svg viewBox="0 0 36 36" style={{ width: '100%', height: '100%' }}>
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="3"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke={summary.overall_success_rate >= 90 ? '#10b981' : summary.overall_success_rate >= 70 ? '#f59e0b' : '#ef4444'}
                    strokeWidth="3"
                    strokeDasharray={`${summary.overall_success_rate}, 100`}
                  />
                </svg>
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 24,
                  fontWeight: 700,
                  color: summary.overall_success_rate >= 90 ? '#10b981' : '#f59e0b',
                }}>
                  {summary.overall_success_rate.toFixed(0)}%
                </div>
              </div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 8 }}>Overall Success Rate</div>
            </div>
          </div>
        </div>
      )}

      {/* Dashboard Tab */}
      {activeTab === 'dashboard' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Analytics Dashboards</h3>
            <select
              value={selectedDashboard}
              onChange={e => setSelectedDashboard(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">All Dashboards</option>
              {dashboards.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>

          {dashboards.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No dashboards available.</div>
          ) : (
            dashboards
              .filter(d => !selectedDashboard || d.id === selectedDashboard)
              .map(dashboard => (
                <div key={dashboard.id} style={{ marginBottom: 24 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <h4 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>{dashboard.name}</h4>
                    <span style={{ fontSize: 12, color: '#9ca3af' }}>Updated: {new Date(dashboard.updated_at).toLocaleString()}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    {dashboard.panels.map(panel => (
                      <div key={panel.id} style={{
                        flex: '1 1 200px',
                        minWidth: 180,
                        background: '#fff',
                        borderRadius: 12,
                        padding: 16,
                        border: '1px solid #e5e7eb',
                      }}>
                        <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>{panel.title}</div>
                        <div style={{ fontSize: 24, fontWeight: 700, color: '#1f2937', marginBottom: 4 }}>
                          {panel.value.toLocaleString()}{panel.unit}
                        </div>
                        <div style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{
                            color: panel.trend >= 0 ? '#10b981' : '#ef4444',
                            fontWeight: 600,
                          }}>
                            {panel.trend >= 0 ? '↑' : '↓'} {Math.abs(panel.trend).toFixed(1)}%
                          </span>
                          <span style={{ color: '#9ca3af' }}>vs previous</span>
                        </div>
                        <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>{panel.metric}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
          )}
        </div>
      )}

      {/* Metrics Tab */}
      {activeTab === 'metrics' && (
        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
            <input
              value={metricSearch}
              onChange={e => setMetricSearch(e.target.value)}
              placeholder="Search metrics..."
              style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
              onKeyDown={e => e.key === 'Enter' && loadMetrics()}
            />
            <select
              value={metricCategory}
              onChange={e => { setMetricCategory(e.target.value); }}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">All Categories</option>
              {[...new Set(metrics.map(m => m.category))].map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <button
              onClick={loadMetrics}
              style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}
            >
              Filter
            </button>
          </div>

          {metrics.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No metrics found.</div>
          ) : (
            <div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
                <thead>
                  <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Name</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Category</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Current Value</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Previous</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Change</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map(metric => (
                    <tr
                      key={metric.id}
                      style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer' }}
                      onClick={() => setSelectedMetric(metric)}
                    >
                      <td style={{ padding: '10px 12px', fontWeight: 500 }}>{metric.name}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 12, fontSize: 11 }}>{metric.category}</span>
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>
                        {metric.current_value.toLocaleString()}{metric.unit}
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>
                        {metric.previous_value.toLocaleString()}{metric.unit}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          color: metric.change_percent >= 0 ? '#10b981' : '#ef4444',
                          fontWeight: 600,
                        }}>
                          {metric.change_percent >= 0 ? '+' : ''}{metric.change_percent.toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{new Date(metric.updated_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {selectedMetric && (
                <div style={{ marginTop: 16, padding: 16, background: '#eff6ff', borderRadius: 12, border: '1px solid #bfdbfe' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <h4 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: '#1e40af' }}>{selectedMetric.name}</h4>
                    <button
                      onClick={() => setSelectedMetric(null)}
                      style={{ padding: '4px 8px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#6b7280' }}
                    >
                      ×
                    </button>
                  </div>
                  <p style={{ fontSize: 13, color: '#374151', margin: '0 0 12px 0' }}>{selectedMetric.description}</p>
                  <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Current: </span>
                      <strong>{selectedMetric.current_value.toLocaleString()}{selectedMetric.unit}</strong>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Previous: </span>
                      <strong>{selectedMetric.previous_value.toLocaleString()}{selectedMetric.unit}</strong>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Change: </span>
                      <strong style={{ color: selectedMetric.change_percent >= 0 ? '#10b981' : '#ef4444' }}>
                        {selectedMetric.change_percent >= 0 ? '+' : ''}{selectedMetric.change_percent.toFixed(1)}%
                      </strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Agent Performance</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={perfSortBy}
                onChange={e => { setPerfSortBy(e.target.value as any); }}
                style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
              >
                <option value="success_rate">Sort by Success Rate</option>
                <option value="efficiency_score">Sort by Efficiency</option>
                <option value="tasks">Sort by Tasks</option>
              </select>
              <button
                onClick={loadPerformance}
                style={{ padding: '6px 12px', background: '#f3f4f6', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
              >
                Refresh
              </button>
            </div>
          </div>

          {performances.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No performance data available.</div>
          ) : (
            <div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, background: '#fff', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
                <thead>
                  <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Agent</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Tasks</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Completed</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Failed</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Success Rate</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Efficiency</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Avg Duration</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Tokens</th>
                    <th style={{ textAlign: 'left', padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {performances.map(perf => (
                    <tr key={perf.agent_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 500 }}>{perf.agent_name}</td>
                      <td style={{ padding: '10px 12px' }}>{perf.total_tasks}</td>
                      <td style={{ padding: '10px 12px', color: '#10b981' }}>{perf.completed_tasks}</td>
                      <td style={{ padding: '10px 12px', color: '#ef4444' }}>{perf.failed_tasks}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{
                            width: 60,
                            height: 6,
                            background: '#e5e7eb',
                            borderRadius: 3,
                            overflow: 'hidden',
                          }}>
                            <div style={{
                              width: `${perf.success_rate}%`,
                              height: '100%',
                              background: perf.success_rate >= 90 ? '#10b981' : perf.success_rate >= 70 ? '#f59e0b' : '#ef4444',
                              borderRadius: 3,
                            }} />
                          </div>
                          <span style={{ fontWeight: 600 }}>{perf.success_rate.toFixed(1)}%</span>
                        </div>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          color: perf.efficiency_score >= 80 ? '#10b981' : perf.efficiency_score >= 50 ? '#f59e0b' : '#ef4444',
                          fontWeight: 600,
                        }}>
                          {perf.efficiency_score.toFixed(0)}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{perf.avg_duration_ms}ms</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>{perf.tokens_used.toLocaleString()}</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: 12 }}>${perf.cost.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>Insights</h3>
            <select
              value={insightSeverity}
              onChange={e => { setInsightSeverity(e.target.value); setInsightPage(1); }}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>

          {insights.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No insights generated yet.</div>
          ) : (
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {insights.map(insight => (
                  <div key={insight.id} style={{
                    background: '#fff',
                    borderRadius: 12,
                    padding: 16,
                    border: '1px solid #e5e7eb',
                    borderLeft: `4px solid ${severityColor(insight.severity)}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <h4 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>{insight.title}</h4>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: severityColor(insight.severity),
                          color: '#fff',
                          fontSize: 11,
                          fontWeight: 600,
                          textTransform: 'uppercase',
                        }}>
                          {insight.severity}
                        </span>
                        <span style={{ fontSize: 11, color: '#6b7280', background: '#f3f4f6', padding: '2px 8px', borderRadius: 12 }}>
                          {insight.category}
                        </span>
                      </div>
                      <span style={{ fontSize: 11, color: '#9ca3af' }}>{new Date(insight.created_at).toLocaleString()}</span>
                    </div>
                    <p style={{ fontSize: 13, color: '#374151', margin: '0 0 8px 0', lineHeight: 1.5 }}>{insight.description}</p>
                    <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
                      {insight.agent_id && <span>Agent: <strong>{insight.agent_id}</strong></span>}
                      {insight.metric && <span>Metric: <strong>{insight.metric}</strong></span>}
                    </div>
                    {insight.recommendation && (
                      <div style={{ padding: '8px 12px', background: '#f0fdf4', borderRadius: 6, border: '1px solid #bbf7d0' }}>
                        <div style={{ fontSize: 11, color: '#059669', fontWeight: 600, marginBottom: 4 }}>RECOMMENDATION</div>
                        <div style={{ fontSize: 13, color: '#065f46' }}>{insight.recommendation}</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
                <button
                  onClick={() => { setInsightPage(p => Math.max(1, p - 1)); loadInsights(); }}
                  disabled={insightPage === 1}
                  style={{ padding: '6px 12px', background: insightPage === 1 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: insightPage === 1 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Previous
                </button>
                <span style={{ padding: '6px 12px', fontSize: 13, color: '#6b7280' }}>Page {insightPage}</span>
                <button
                  onClick={() => { setInsightPage(p => p + 1); loadInsights(); }}
                  disabled={insights.length < 20}
                  style={{ padding: '6px 12px', background: insights.length < 20 ? '#f3f4f6' : '#e5e7eb', border: 'none', borderRadius: 6, cursor: insights.length < 20 ? 'default' : 'pointer', fontSize: 12 }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};