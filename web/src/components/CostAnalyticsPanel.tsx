import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

// ── Types ──

interface CostSummary {
  total_cost: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
  model_breakdown: Record<string, { cost: number; tokens: number; requests: number }>;
  avg_cost_per_request: number;
}

interface OptimizationSuggestion {
  type: string;
  description: string;
  estimated_savings: number;
  action: string;
}

interface BudgetStatus {
  daily: { spent: number; limit: number; percent: number };
  weekly: { spent: number; limit: number; percent: number };
  monthly: { spent: number; limit: number; percent: number };
}

type Period = 'daily' | 'weekly' | 'monthly';

// ── Helpers ──

function formatCost(cents: number): string {
  return `$${(cents / 100).toFixed(4)}`;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

const TIER_LABELS: Record<string, string> = {
  light: 'Light',
  standard: 'Standard',
  premium: 'Premium',
};

const TIER_COLORS: Record<string, string> = {
  light: '#22c55e',
  standard: '#3b82f6',
  premium: '#8b5cf6',
};

// ── Component ──

export const CostAnalyticsPanel: React.FC = () => {
  const toast = useToast();

  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [byTier, setByTier] = useState<Record<string, { cost: number; requests: number }>>({});
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [budgets, setBudgets] = useState<BudgetStatus | null>(null);
  const [dailyCosts, setDailyCosts] = useState<Array<{ date: string; cost: number }>>([]);
  const [period, setPeriod] = useState<Period>('daily');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [overviewRes, breakdownRes, byTierRes, suggestionsRes, budgetsRes] = await Promise.all([
        api.costs.overview(),
        api.costs.breakdown(period),
        api.costs.byTier(),
        api.costs.suggestions(),
        api.costs.budgets(),
      ]);
      setSummary(overviewRes as CostSummary);
      setDailyCosts(Array.isArray(breakdownRes) ? breakdownRes : []);
      setByTier(byTierRes || {});
      setSuggestions(Array.isArray(suggestionsRes) ? suggestionsRes : []);
      setBudgets(budgetsRes as BudgetStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cost analytics');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadData();
    }, 30_000);
    return () => clearInterval(interval);
  }, [loadData]);

  // ── Render helpers ──

  const getBudgetSeverity = (percent: number): 'normal' | 'warning' | 'critical' => {
    if (percent >= 90) return 'critical';
    if (percent >= 70) return 'warning';
    return 'normal';
  };

  const budgetSeverityColors: Record<string, string> = {
    normal: '#22c55e',
    warning: '#f59e0b',
    critical: '#ef4444',
  };

  const maxDailyCost = Math.max(...dailyCosts.map((d) => d.cost), 1);

  // ── Loading ──

  if (loading && !summary) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Cost Analytics</h2>
          <div className="panel-subtitle">Token cost tracking and optimization</div>
        </div>
        <div className="panel-loading">Loading cost analytics...</div>
      </div>
    );
  }

  // ── Main render ──

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>Cost Analytics</h2>
          <div className="panel-subtitle">Token cost tracking and optimization</div>
        </div>
        <div className="panel-actions">
          <button className="btn-sm btn-secondary" onClick={loadData}>
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="panel-error">
          {error}
          <button className="btn-sm" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* ── Period Filter ── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {(['daily', 'weekly', 'monthly'] as Period[]).map((p) => (
          <button
            key={p}
            className={`btn-sm ${period === p ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setPeriod(p)}
            style={{ textTransform: 'capitalize' }}
          >
            {p}
          </button>
        ))}
      </div>

      {/* ── Cost Summary Cards ── */}
      {summary && (
        <div className="memory-stats-grid">
          <div className="memory-stat-card">
            <div className="memory-stat-value">{formatCost(summary.total_cost)}</div>
            <div className="memory-stat-label">Total Cost</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{formatTokens(summary.total_tokens)}</div>
            <div className="memory-stat-label">Total Tokens</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{formatNumber(summary.request_count)}</div>
            <div className="memory-stat-label">Request Count</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{formatCost(summary.avg_cost_per_request)}</div>
            <div className="memory-stat-label">Avg Cost / Request</div>
          </div>
        </div>
      )}

      {/* ── Budget Status ── */}
      {budgets && (
        <div className="dashboard-section">
          <h3>Budget Status</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {(['daily', 'weekly', 'monthly'] as const).map((key) => {
              const b = budgets[key];
              const severity = getBudgetSeverity(b.percent);
              const color = budgetSeverityColors[severity];
              return (
                <div
                  key={key}
                  className="memory-stat-card"
                  style={{ padding: 12, textAlign: 'left' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, textTransform: 'capitalize', fontSize: '0.85rem' }}>
                      {key}
                    </span>
                    <span style={{ fontSize: '0.8rem', color }}>{b.percent.toFixed(1)}%</span>
                  </div>
                  <div
                    style={{
                      height: 8,
                      background: 'var(--border)',
                      borderRadius: 4,
                      overflow: 'hidden',
                      marginBottom: 8,
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(b.percent, 100)}%`,
                        background: color,
                        borderRadius: 4,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>{formatCost(b.spent)} spent</span>
                    <span>{formatCost(b.limit)} limit</span>
                  </div>
                  {severity === 'critical' && (
                    <div style={{ marginTop: 8, fontSize: '0.75rem', color: '#ef4444', fontWeight: 600 }}>
                      Critical: Budget nearly exhausted
                    </div>
                  )}
                  {severity === 'warning' && (
                    <div style={{ marginTop: 8, fontSize: '0.75rem', color: '#f59e0b', fontWeight: 600 }}>
                      Warning: Budget usage high
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Model Breakdown ── */}
      {summary && Object.keys(summary.model_breakdown).length > 0 && (
        <div className="dashboard-section">
          <h3>Model Breakdown</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                  <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600 }}>Model</th>
                  <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'right' }}>Cost</th>
                  <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'right' }}>Tokens</th>
                  <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'right' }}>Requests</th>
                  <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'right' }}>Share</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.model_breakdown)
                  .sort(([, a], [, b]) => b.cost - a.cost)
                  .map(([model, data]) => {
                    const share = summary.total_cost > 0
                      ? ((data.cost / summary.total_cost) * 100).toFixed(1)
                      : '0.0';
                    return (
                      <tr
                        key={model}
                        style={{ borderBottom: '1px solid var(--border)' }}
                      >
                        <td style={{ padding: '8px 12px', fontWeight: 500 }}>{model}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--blue)' }}>
                          {formatCost(data.cost)}
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                          {formatTokens(data.tokens)}
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                          {formatNumber(data.requests)}
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                          {share}%
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Cost by Tier ── */}
      {Object.keys(byTier).length > 0 && (
        <div className="dashboard-section">
          <h3>Cost by Tier</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {Object.entries(byTier).map(([tier, data]) => {
              const maxTierCost = Math.max(...Object.values(byTier).map((d) => d.cost), 1);
              const barPct = (data.cost / maxTierCost) * 100;
              return (
                <div key={tier}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: '0.85rem' }}>
                    <span style={{ fontWeight: 500 }}>
                      {TIER_LABELS[tier] || tier}
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {formatCost(data.cost)} · {data.requests} requests
                    </span>
                  </div>
                  <div
                    style={{
                      height: 12,
                      background: 'var(--border)',
                      borderRadius: 6,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${barPct}%`,
                        background: TIER_COLORS[tier] || '#6b7280',
                        borderRadius: 6,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Daily Cost Chart ── */}
      {dailyCosts.length > 0 && (
        <div className="dashboard-section">
          <h3>
            {period === 'daily' ? 'Daily' : period === 'weekly' ? 'Weekly' : 'Monthly'} Cost Trend
          </h3>
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 4,
              height: 160,
              paddingTop: 8,
            }}
          >
            {dailyCosts.map((day, idx) => {
              const heightPct = maxDailyCost > 0 ? (day.cost / maxDailyCost) * 100 : 0;
              return (
                <div
                  key={day.date || idx}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 4,
                    minWidth: 0,
                  }}
                  title={`${day.date}: ${formatCost(day.cost)}`}
                >
                  <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
                    {formatCost(day.cost)}
                  </span>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: 40,
                      height: `${Math.max(heightPct, 2)}%`,
                      background: 'var(--blue)',
                      borderRadius: '4px 4px 0 0',
                      transition: 'height 0.3s ease',
                      minHeight: 2,
                    }}
                  />
                  <span
                    style={{
                      fontSize: '0.6rem',
                      color: 'var(--text-muted)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '100%',
                    }}
                  >
                    {day.date ? day.date.slice(5) : ''}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Optimization Suggestions ── */}
      {suggestions.length > 0 && (
        <div className="dashboard-section">
          <h3>Optimization Suggestions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {suggestions.map((s, idx) => (
              <div
                key={idx}
                className="memory-stat-card"
                style={{ padding: 12, textAlign: 'left' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: 4 }}>
                      {s.type}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 4 }}>
                      {s.description}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--blue)' }}>
                      Action: {s.action}
                    </div>
                  </div>
                  <div
                    style={{
                      background: 'rgba(34, 197, 94, 0.1)',
                      color: '#22c55e',
                      padding: '4px 10px',
                      borderRadius: 12,
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    Save {formatCost(s.estimated_savings)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Empty State ── */}
      {!summary && !error && (
        <div className="panel-empty">
          <p>No cost data available.</p>
          <p>Run some agents to start tracking token costs.</p>
        </div>
      )}
    </div>
  );
};