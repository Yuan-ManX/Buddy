import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface SentienceStats {
  total_cycles: number;
  success_rate: number;
  state: string;
  uptime_seconds: number;
  last_cycle_at: string | null;
}

interface SentienceIdentity {
  name: string;
  role: string;
  traits: string[];
  version: string;
  created_at: string;
}

interface SentienceCycle {
  cycle_id: string;
  cycle_number: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  summary: string;
}

interface SentienceInsight {
  insight_id: string;
  content: string;
  category: string;
  confidence: number;
  created_at: string;
}

interface SentienceGoal {
  goal_id: string;
  description: string;
  priority: number;
  completion: number;
  status: string;
  created_at: string;
}

interface SentiencePerception {
  perception_id: string;
  source: string;
  content: string;
  relevance: number;
  timestamp: string;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const SentienceCorePanel: React.FC = () => {
  const toast = useToast();

  // ── State ──
  const [stats, setStats] = useState<SentienceStats | null>(null);
  const [identity, setIdentity] = useState<SentienceIdentity | null>(null);
  const [cycles, setCycles] = useState<SentienceCycle[]>([]);
  const [insights, setInsights] = useState<SentienceInsight[]>([]);
  const [goals, setGoals] = useState<SentienceGoal[]>([]);
  const [perceptions, setPerceptions] = useState<SentiencePerception[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<
    'overview' | 'identity' | 'cycles' | 'insights' | 'goals' | 'perceptions'
  >('overview');
  const [cycling, setCycling] = useState(false);

  // ── Data Loading ──

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, id, cy, ins, g, p] = await Promise.all([
        request<SentienceStats>('/sentience/stats').catch(() => null),
        request<SentienceIdentity>('/sentience/identity').catch(() => null),
        request<SentienceCycle[]>('/sentience/cycles').catch(() => []),
        request<SentienceInsight[]>('/sentience/insights').catch(() => []),
        request<SentienceGoal[]>('/sentience/goals').catch(() => []),
        request<SentiencePerception[]>('/sentience/perceptions').catch(() => []),
      ]);
      setStats(s);
      setIdentity(id);
      setCycles(Array.isArray(cy) ? cy : (cy as any)?.cycles || []);
      setInsights(Array.isArray(ins) ? ins : (ins as any)?.insights || []);
      setGoals(Array.isArray(g) ? g : (g as any)?.goals || []);
      setPerceptions(Array.isArray(p) ? p : (p as any)?.perceptions || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load sentience core data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Handlers ──

  const handleRunCycle = async () => {
    try {
      setCycling(true);
      const result = await request<any>('/sentience/cycle', { method: 'POST' });
      toast.success(result.message || 'Cycle executed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setCycling(false);
    }
  };

  // ── Helpers ──

  const cycleStatusColors: Record<string, string> = {
    completed: '#22c55e',
    running: '#3b82f6',
    failed: '#ef4444',
    pending: '#f59e0b',
    cancelled: '#9ca3af',
  };

  const stateColor = (state: string): string => {
    switch (state) {
      case 'active':
        return '#22c55e';
      case 'idle':
        return '#f59e0b';
      case 'error':
        return '#ef4444';
      case 'initializing':
        return '#3b82f6';
      default:
        return '#9ca3af';
    }
  };

  const goalStatusColors: Record<string, string> = {
    active: '#22c55e',
    completed: '#3b82f6',
    paused: '#f59e0b',
    abandoned: '#9ca3af',
  };

  const confidenceColor = (c: number): string => {
    if (c >= 0.8) return '#22c55e';
    if (c >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  // ── Loading State ──

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Sentience Core</h2>
          <p className="panel-subtitle">Core consciousness and self-awareness engine</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading sentience core data...</span>
        </div>
      </div>
    );
  }

  // ── Main Render ──

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Sentience Core</h2>
        <p className="panel-subtitle">Core consciousness, reflection, goal management, and perception engine</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_cycles}</span>
              <span className="stat-label">Total Cycles</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>
                {(stats.success_rate * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Success Rate</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stateColor(stats.state) }}>
                {stats.state}
              </span>
              <span className="stat-label">State</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{Math.floor(stats.uptime_seconds / 3600)}h</span>
              <span className="stat-label">Uptime</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ fontSize: '0.85rem' }}>
                {stats.last_cycle_at ? new Date(stats.last_cycle_at).toLocaleString() : 'Never'}
              </span>
              <span className="stat-label">Last Cycle</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'identity', 'cycles', 'insights', 'goals', 'perceptions'] as const).map((s) => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Core Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Cycles</span>
                <strong>{stats.total_cycles}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Success Rate</span>
                <strong style={{ color: stats.success_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                  {(stats.success_rate * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Current State</span>
                <strong style={{ color: stateColor(stats.state) }}>{stats.state}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Uptime</span>
                <strong>{Math.floor(stats.uptime_seconds / 3600)}h {Math.floor((stats.uptime_seconds % 3600) / 60)}m</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Insights Generated</span>
                <strong style={{ color: '#8b5cf6' }}>{insights.length}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Active Goals</span>
                <strong style={{ color: '#22c55e' }}>
                  {goals.filter((g) => g.status === 'active').length}
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Perception Buffer</span>
                <strong style={{ color: '#3b82f6' }}>{perceptions.length} entries</strong>
              </div>

              <div style={{ marginTop: 20 }}>
                <button
                  className="btn-primary"
                  onClick={handleRunCycle}
                  disabled={cycling}
                  style={{ background: '#8b5cf6' }}
                >
                  {cycling ? 'Running...' : 'Run Test Cycle'}
                </button>
              </div>

              {/* Recent Cycles */}
              <h3 style={{ marginTop: 24 }}>Recent Cycles</h3>
              {cycles.length === 0 ? (
                <div className="panel-empty">No cycles recorded yet</div>
              ) : (
                <div className="forge-skill-list">
                  {cycles.slice(0, 5).map((cycle) => (
                    <div key={cycle.cycle_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">Cycle #{cycle.cycle_number}</div>
                        <span
                          className="dashboard-badge"
                          style={{
                            background: cycleStatusColors[cycle.status] || '#9ca3af',
                            color: '#fff',
                          }}
                        >
                          {cycle.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{cycle.summary}</div>
                        <div>
                          Started: {new Date(cycle.started_at).toLocaleString()}
                          {cycle.completed_at && ` | Completed: ${new Date(cycle.completed_at).toLocaleString()}`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Recent Insights */}
              <h3 style={{ marginTop: 24 }}>Recent Insights</h3>
              {insights.length === 0 ? (
                <div className="panel-empty">No insights generated yet</div>
              ) : (
                <div className="forge-skill-list">
                  {insights.slice(0, 3).map((insight) => (
                    <div key={insight.insight_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ fontSize: '0.9rem' }}>
                          {insight.content}
                        </div>
                        <span
                          className="dashboard-badge"
                          style={{
                            background: confidenceColor(insight.confidence),
                            color: '#fff',
                          }}
                        >
                          {insight.category} ({Math.round(insight.confidence * 100)}%)
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Created: {new Date(insight.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Identity Section ── */}
      {activeSection === 'identity' && (
        <div className="dashboard-section">
          <h3>Identity Configuration</h3>
          {identity ? (
            <>
              <div
                style={{
                  padding: 16,
                  background: '#f8fafc',
                  borderRadius: 8,
                  marginBottom: 16,
                }}
              >
                <div className="dashboard-stat-row">
                  <span>Name</span>
                  <strong>{identity.name}</strong>
                </div>
                <div className="dashboard-stat-row">
                  <span>Role</span>
                  <strong style={{ color: '#4f6ef7' }}>{identity.role}</strong>
                </div>
                <div className="dashboard-stat-row">
                  <span>Version</span>
                  <strong>{identity.version}</strong>
                </div>
                <div className="dashboard-stat-row">
                  <span>Created</span>
                  <strong>{new Date(identity.created_at).toLocaleString()}</strong>
                </div>
              </div>

              <h4>Traits</h4>
              {identity.traits && identity.traits.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {identity.traits.map((trait, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: '6px 14px',
                        background: '#ede9fe',
                        color: '#7c3aed',
                        borderRadius: 20,
                        fontSize: '0.85rem',
                        fontWeight: 500,
                      }}
                    >
                      {trait}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No traits defined</div>
              )}
            </>
          ) : (
            <div className="panel-empty">No identity data available</div>
          )}
        </div>
      )}

      {/* ── Cycles Section ── */}
      {activeSection === 'cycles' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3>Cycles ({cycles.length})</h3>
            <button
              className="btn-primary"
              onClick={handleRunCycle}
              disabled={cycling}
              style={{ background: '#8b5cf6' }}
            >
              {cycling ? 'Running...' : 'Run Cycle'}
            </button>
          </div>

          {cycles.length === 0 ? (
            <div className="panel-empty">No cycles recorded yet. Click "Run Cycle" to start one.</div>
          ) : (
            <div className="forge-skill-list">
              {cycles.map((cycle) => (
                <div key={cycle.cycle_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Cycle #{cycle.cycle_number}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: cycleStatusColors[cycle.status] || '#9ca3af',
                        color: '#fff',
                      }}
                    >
                      {cycle.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{cycle.summary}</div>
                    <div>
                      Started: {new Date(cycle.started_at).toLocaleString()}
                    </div>
                    {cycle.completed_at && (
                      <div>Completed: {new Date(cycle.completed_at).toLocaleString()}</div>
                    )}
                    <div>Cycle ID: {cycle.cycle_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Insights Section ── */}
      {activeSection === 'insights' && (
        <div className="dashboard-section">
          <h3>Reflection Insights ({insights.length})</h3>

          {insights.length === 0 ? (
            <div className="panel-empty">No insights generated yet</div>
          ) : (
            <div className="forge-skill-list">
              {insights.map((insight) => (
                <div key={insight.insight_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.9rem' }}>
                      {insight.content}
                    </div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: confidenceColor(insight.confidence),
                        color: '#fff',
                      }}
                    >
                      {Math.round(insight.confidence * 100)}%
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Category: {insight.category}</div>
                    <div>Created: {new Date(insight.created_at).toLocaleString()}</div>
                    <div>ID: {insight.insight_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Goals Section ── */}
      {activeSection === 'goals' && (
        <div className="dashboard-section">
          <h3>Goals Management ({goals.length})</h3>

          {goals.length === 0 ? (
            <div className="panel-empty">No goals configured</div>
          ) : (
            <div className="forge-skill-list">
              {goals.map((goal) => (
                <div key={goal.goal_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{goal.description}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: goalStatusColors[goal.status] || '#9ca3af',
                        color: '#fff',
                      }}
                    >
                      {goal.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Priority: {goal.priority}</div>
                    <div style={{ marginTop: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: '0.85rem', color: '#6b7280', minWidth: 80 }}>
                          Completion
                        </span>
                        <div
                          style={{
                            flex: 1,
                            height: 8,
                            background: '#e5e7eb',
                            borderRadius: 4,
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${Math.min(goal.completion * 100, 100)}%`,
                              height: '100%',
                              background:
                                goal.completion >= 1
                                  ? '#22c55e'
                                  : goal.completion >= 0.5
                                  ? '#3b82f6'
                                  : '#f59e0b',
                              borderRadius: 4,
                              transition: 'width 0.3s ease',
                            }}
                          />
                        </div>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, minWidth: 40 }}>
                          {Math.round(goal.completion * 100)}%
                        </span>
                      </div>
                    </div>
                    <div>Created: {new Date(goal.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Perceptions Section ── */}
      {activeSection === 'perceptions' && (
        <div className="dashboard-section">
          <h3>Perception Buffer ({perceptions.length})</h3>

          {perceptions.length === 0 ? (
            <div className="panel-empty">Perception buffer is empty</div>
          ) : (
            <div className="forge-skill-list">
              {perceptions.map((perception) => (
                <div key={perception.perception_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.9rem' }}>
                      {perception.content}
                    </div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: perception.relevance >= 0.7 ? '#22c55e' : '#f59e0b',
                        color: '#fff',
                      }}
                    >
                      Relevance: {Math.round(perception.relevance * 100)}%
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Source: {perception.source}</div>
                    <div>Timestamp: {new Date(perception.timestamp).toLocaleString()}</div>
                    <div>ID: {perception.perception_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SentienceCorePanel;