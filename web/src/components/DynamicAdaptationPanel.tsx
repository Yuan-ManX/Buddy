import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface DynamicAdaptationStats {
  total_sessions: number;
  deviations_detected: number;
  adaptations_applied: number;
  adaptation_success_rate: number;
  lessons_learned: number;
}

interface Checkpoint {
  name: string;
  status: string;
  completed_at?: string;
}

interface MonitorMetric {
  name: string;
  value: number;
  unit?: string;
}

interface MonitorSession {
  session_id: string;
  plan_id: string;
  status: string;
  checkpoints: Checkpoint[];
  metrics: MonitorMetric[];
  started_at: string;
}

interface AdaptationRecord {
  id: string;
  deviation_type: string;
  adaptation_strategy: string;
  original_plan: string;
  adapted_plan: string;
  confidence: number;
  applied_at: string;
}

interface Lesson {
  id: string;
  deviation_type: string;
  learned_pattern: string;
  effectiveness: number;
  times_encountered: number;
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

export const DynamicAdaptationPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<DynamicAdaptationStats | null>(null);
  const [adaptations, setAdaptations] = useState<AdaptationRecord[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'monitor' | 'adaptations' | 'lessons'>('overview');

  // Monitor form
  const [planId, setPlanId] = useState('');
  const [monitoring, setMonitoring] = useState(false);
  const [monitorSession, setMonitorSession] = useState<MonitorSession | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, a, l] = await Promise.all([
        request<DynamicAdaptationStats>('/dynamic-adaptation/stats').catch(() => null),
        request<AdaptationRecord[]>('/dynamic-adaptation/history').catch(() => []),
        request<Lesson[]>('/dynamic-adaptation/lessons').catch(() => []),
      ]);
      setStats(s);
      setAdaptations(Array.isArray(a) ? a : (a as any)?.adaptations || []);
      setLessons(Array.isArray(l) ? l : (l as any)?.lessons || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load dynamic adaptation data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleMonitor = async () => {
    if (!planId.trim()) return;
    try {
      setMonitoring(true);
      const result = await request<MonitorSession>('/dynamic-adaptation/monitor', {
        method: 'POST',
        body: JSON.stringify({ plan_id: planId }),
      });
      setMonitorSession(result);
      toast.success(result.session_id ? `Monitoring started for session ${result.session_id}` : 'Monitoring started');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setMonitoring(false);
    }
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    completed: '#22c55e',
    monitoring: '#3b82f6',
    failed: '#ef4444',
    pending: '#f59e0b',
    adapted: '#8b5cf6',
    warning: '#f59e0b',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Dynamic Adaptation Engine</h2>
          <p className="panel-subtitle">Monitor execution plans and adapt to deviations in real time</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading dynamic adaptation data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Dynamic Adaptation Engine</h2>
        <p className="panel-subtitle">Monitor execution, detect deviations, and adapt plans intelligently</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_sessions}</span>
              <span className="stat-label">Total Sessions</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>{stats.deviations_detected}</span>
              <span className="stat-label">Deviations Detected</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.adaptations_applied}</span>
              <span className="stat-label">Adaptations Applied</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stats.adaptation_success_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                {(stats.adaptation_success_rate * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Success Rate</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#06b6d4' }}>{stats.lessons_learned}</span>
              <span className="stat-label">Lessons Learned</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab Bar */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'monitor', 'adaptations', 'lessons'] as const).map(t => (
          <button
            key={t}
            className={`forge-tab ${activeTab === t ? 'active' : ''}`}
            onClick={() => setActiveTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {activeTab === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Adaptation Engine Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Sessions</span>
                <strong>{stats.total_sessions}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Deviations Detected</span>
                <strong style={{ color: '#f59e0b' }}>{stats.deviations_detected}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Adaptations Applied</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.adaptations_applied}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Adaptation Success Rate</span>
                <strong style={{ color: stats.adaptation_success_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                  {(stats.adaptation_success_rate * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Lessons Learned</span>
                <strong style={{ color: '#06b6d4' }}>{stats.lessons_learned}</strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Recent Adaptations</h3>
              {adaptations.length === 0 ? (
                <div className="panel-empty">No adaptations recorded yet</div>
              ) : (
                <div className="forge-skill-list">
                  {adaptations.slice(0, 5).map(adaptation => (
                    <div key={adaptation.id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{adaptation.deviation_type}</div>
                        <span className="dashboard-badge" style={{
                          background: '#8b5cf6',
                          color: '#fff',
                        }}>
                          {(adaptation.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Strategy: {adaptation.adaptation_strategy}</div>
                        <div>Applied: {new Date(adaptation.applied_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Monitor Tab ── */}
      {activeTab === 'monitor' && (
        <div className="dashboard-section">
          <h3>Monitor Execution</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Plan ID</label>
              <input
                type="text"
                value={planId}
                onChange={e => setPlanId(e.target.value)}
                placeholder="Enter the plan ID to monitor..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleMonitor}
              disabled={monitoring || !planId.trim()}
            >
              {monitoring ? 'Starting...' : 'Start Monitoring'}
            </button>
          </div>

          {monitorSession && (
            <div className="dashboard-section" style={{ marginTop: 16 }}>
              <h3>Monitor Session</h3>
              <div className="dashboard-stat-row">
                <span>Session ID</span>
                <strong>{monitorSession.session_id}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Plan ID</span>
                <strong>{monitorSession.plan_id}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Status</span>
                <strong style={{ color: statusColors[monitorSession.status] || '#9ca3af' }}>
                  {monitorSession.status}
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Started At</span>
                <strong>{new Date(monitorSession.started_at).toLocaleString()}</strong>
              </div>

              {monitorSession.checkpoints && monitorSession.checkpoints.length > 0 && (
                <>
                  <h3 style={{ marginTop: 20 }}>Checkpoints</h3>
                  <div className="forge-skill-list">
                    {monitorSession.checkpoints.map((cp, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{cp.name}</div>
                          <span className="dashboard-badge" style={{
                            background: statusColors[cp.status] || '#9ca3af',
                            color: '#fff',
                          }}>
                            {cp.status}
                          </span>
                        </div>
                        {cp.completed_at && (
                          <div className="forge-skill-meta">
                            <div>Completed: {new Date(cp.completed_at).toLocaleString()}</div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}

              {monitorSession.metrics && monitorSession.metrics.length > 0 && (
                <>
                  <h3 style={{ marginTop: 20 }}>Metrics</h3>
                  <div className="forge-skill-list">
                    {monitorSession.metrics.map((m, i) => (
                      <div key={i} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{m.name}</div>
                          <span className="dashboard-badge" style={{
                            background: '#3b82f6',
                            color: '#fff',
                          }}>
                            {m.value}{m.unit ? ` ${m.unit}` : ''}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Adaptations Tab ── */}
      {activeTab === 'adaptations' && (
        <div className="dashboard-section">
          <h3>Adaptation History ({adaptations.length})</h3>
          {adaptations.length === 0 ? (
            <div className="panel-empty">No adaptation records yet. Start monitoring a plan to generate adaptations.</div>
          ) : (
            <div className="forge-skill-list">
              {adaptations.map(adaptation => (
                <div key={adaptation.id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{adaptation.deviation_type}</div>
                    <span className="dashboard-badge" style={{
                      background: '#8b5cf6',
                      color: '#fff',
                    }}>
                      {(adaptation.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Strategy: {adaptation.adaptation_strategy}</div>
                    <div>Original Plan: {adaptation.original_plan}</div>
                    <div>Adapted Plan: {adaptation.adapted_plan}</div>
                    <div>Applied: {new Date(adaptation.applied_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Lessons Tab ── */}
      {activeTab === 'lessons' && (
        <div className="dashboard-section">
          <h3>Learned Lessons ({lessons.length})</h3>
          {lessons.length === 0 ? (
            <div className="panel-empty">No lessons learned yet. Adaptations will generate lessons over time.</div>
          ) : (
            <div className="forge-skill-list">
              {lessons.map(lesson => (
                <div key={lesson.id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{lesson.deviation_type}</div>
                    <span className="dashboard-badge" style={{
                      background: lesson.effectiveness >= 0.7 ? '#22c55e' : '#f59e0b',
                      color: '#fff',
                    }}>
                      {(lesson.effectiveness * 100).toFixed(0)}% effective
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Pattern: {lesson.learned_pattern}</div>
                    <div>Times Encountered: {lesson.times_encountered}</div>
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

export default DynamicAdaptationPanel;