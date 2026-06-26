import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface AutotunerStats {
  total_components: number;
  bottlenecks_found: number;
  optimizations_applied: number;
  overall_improvement: number;
}

interface PerformanceProfile {
  component_id: string;
  component_type: string;
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  throughput: number;
  error_rate: number;
  resource_usage: Record<string, number>;
  cache_hit_rate: number;
}

interface Bottleneck {
  component_id: string;
  type: string;
  severity: string;
  current_value: number;
  threshold: number;
  impact: string;
}

interface TuningResult {
  component_id: string;
  optimizations_applied: string[];
  overall_improvement: number;
  recommendations: string[];
}

interface AutotunerReport {
  components: PerformanceProfile[];
  bottlenecks: Bottleneck[];
  optimizations: TuningResult[];
  overall_improvement: number;
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

export const PerformanceAutotunerPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<AutotunerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'profile' | 'bottlenecks' | 'tune' | 'report'>('overview');

  // Profile form
  const [profileForm, setProfileForm] = useState({
    component_id: '',
    component_type: 'model_router',
  });
  const [profiling, setProfiling] = useState(false);
  const [profile, setProfile] = useState<PerformanceProfile | null>(null);

  // Bottlenecks
  const [bottlenecks, setBottlenecks] = useState<Bottleneck[]>([]);
  const [bottlenecksLoading, setBottlenecksLoading] = useState(false);
  const [recommending, setRecommending] = useState<string | null>(null);

  // Tune form
  const [tuneComponentId, setTuneComponentId] = useState('');
  const [tuning, setTuning] = useState(false);
  const [tuningResult, setTuningResult] = useState<TuningResult | null>(null);

  // Report
  const [report, setReport] = useState<AutotunerReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await request<AutotunerStats>('/performance-autotuner/stats').catch(() => null);
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load performance autotuner data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleProfile = async () => {
    if (!profileForm.component_id.trim()) return;
    try {
      setProfiling(true);
      const result = await request<PerformanceProfile>('/performance-autotuner/profile', {
        method: 'POST',
        body: JSON.stringify({
          component_id: profileForm.component_id,
          component_type: profileForm.component_type,
        }),
      });
      setProfile(result);
      toast.success('Profile generated successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setProfiling(false);
    }
  };

  const loadBottlenecks = useCallback(async () => {
    try {
      setBottlenecksLoading(true);
      const result = await request<Bottleneck[]>('/performance-autotuner/bottlenecks');
      setBottlenecks(Array.isArray(result) ? result : (result as any)?.bottlenecks || []);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setBottlenecksLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (activeTab === 'bottlenecks') {
      loadBottlenecks();
    }
  }, [activeTab, loadBottlenecks]);

  const handleRecommend = async (componentId: string) => {
    try {
      setRecommending(componentId);
      const result = await request<any>(`/performance-autotuner/recommend`, {
        method: 'POST',
        body: JSON.stringify({ component_id: componentId }),
      });
      toast.success(result.message || `Recommendations generated for ${componentId}`);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRecommending(null);
    }
  };

  const handleAutoTune = async () => {
    if (!tuneComponentId.trim()) return;
    try {
      setTuning(true);
      const result = await request<TuningResult>('/performance-autotuner/auto-tune', {
        method: 'POST',
        body: JSON.stringify({ component_id: tuneComponentId }),
      });
      setTuningResult(result);
      toast.success('Auto-tuning completed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setTuning(false);
    }
  };

  const loadReport = useCallback(async () => {
    try {
      setReportLoading(true);
      const result = await request<AutotunerReport>('/performance-autotuner/report');
      setReport(result);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setReportLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (activeTab === 'report') {
      loadReport();
    }
  }, [activeTab, loadReport]);

  const severityColors: Record<string, string> = {
    critical: '#ef4444',
    high: '#f97316',
    medium: '#f59e0b',
    low: '#22c55e',
    info: '#3b82f6',
  };

  const componentTypes = [
    'model_router',
    'tool_executor',
    'cache',
    'memory',
    'pipeline',
    'api_endpoint',
    'database',
    'streaming',
  ];

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Performance Autotuner</h2>
          <p className="panel-subtitle">Profile, detect bottlenecks, and auto-tune system components</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading performance autotuner data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Performance Autotuner</h2>
        <p className="panel-subtitle">Profile, detect bottlenecks, and auto-tune system components for optimal performance</p>
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
              <span className="stat-value">{stats.total_components}</span>
              <span className="stat-label">Total Components</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stats.bottlenecks_found > 0 ? '#ef4444' : '#22c55e' }}>
                {stats.bottlenecks_found}
              </span>
              <span className="stat-label">Bottlenecks Found</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.optimizations_applied}</span>
              <span className="stat-label">Optimizations Applied</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stats.overall_improvement > 0 ? '#22c55e' : '#f59e0b' }}>
                {stats.overall_improvement.toFixed(1)}%
              </span>
              <span className="stat-label">Overall Improvement</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'profile', 'bottlenecks', 'tune', 'report'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeTab === s ? 'active' : ''}`}
            onClick={() => setActiveTab(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeTab === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Autotuner Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Components</span>
                <strong>{stats.total_components}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Bottlenecks Found</span>
                <strong style={{ color: stats.bottlenecks_found > 0 ? '#ef4444' : '#22c55e' }}>
                  {stats.bottlenecks_found}
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Optimizations Applied</span>
                <strong style={{ color: '#3b82f6' }}>{stats.optimizations_applied}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Overall Improvement</span>
                <strong style={{ color: stats.overall_improvement > 0 ? '#22c55e' : '#f59e0b' }}>
                  {stats.overall_improvement.toFixed(1)}%
                </strong>
              </div>
            </>
          )}
          {!stats && (
            <div className="panel-empty">No stats available. Use the Profile tab to get started.</div>
          )}
        </div>
      )}

      {/* ── Profile Section ── */}
      {activeTab === 'profile' && (
        <div className="dashboard-section">
          <h3>Profile Component</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Component ID</label>
              <input
                type="text"
                value={profileForm.component_id}
                onChange={e => setProfileForm(f => ({ ...f, component_id: e.target.value }))}
                placeholder="Enter component ID..."
              />
            </div>
            <div className="form-group">
              <label>Component Type</label>
              <select
                value={profileForm.component_type}
                onChange={e => setProfileForm(f => ({ ...f, component_type: e.target.value }))}
              >
                {componentTypes.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <button
              className="btn-primary"
              onClick={handleProfile}
              disabled={profiling || !profileForm.component_id.trim()}
            >
              {profiling ? 'Profiling...' : 'Profile'}
            </button>
          </div>

          {profile && (
            <div className="dashboard-section">
              <h3>Performance Profile: {profile.component_id}</h3>
              <div className="dashboard-stat-row">
                <span>Component Type</span>
                <strong>{profile.component_type}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Avg Latency</span>
                <strong>{profile.avg_latency_ms.toFixed(2)}ms</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>P95 Latency</span>
                <strong style={{ color: '#f97316' }}>{profile.p95_latency_ms.toFixed(2)}ms</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>P99 Latency</span>
                <strong style={{ color: '#ef4444' }}>{profile.p99_latency_ms.toFixed(2)}ms</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Throughput</span>
                <strong>{profile.throughput.toFixed(2)} req/s</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Error Rate</span>
                <strong style={{ color: profile.error_rate > 0.05 ? '#ef4444' : '#22c55e' }}>
                  {(profile.error_rate * 100).toFixed(2)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Cache Hit Rate</span>
                <strong style={{ color: profile.cache_hit_rate > 0.8 ? '#22c55e' : '#f59e0b' }}>
                  {(profile.cache_hit_rate * 100).toFixed(1)}%
                </strong>
              </div>
              {profile.resource_usage && Object.keys(profile.resource_usage).length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Resource Usage</h4>
                  {Object.entries(profile.resource_usage).map(([key, value]) => (
                    <div className="dashboard-stat-row" key={key}>
                      <span>{key}</span>
                      <strong>{typeof value === 'number' ? value.toFixed(2) : String(value)}</strong>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Bottlenecks Section ── */}
      {activeTab === 'bottlenecks' && (
        <div className="dashboard-section">
          <h3>Detected Bottlenecks</h3>
          {bottlenecksLoading ? (
            <div className="panel-loading">
              <div className="spinner" />
              <span>Loading bottlenecks...</span>
            </div>
          ) : bottlenecks.length === 0 ? (
            <div className="panel-empty">No bottlenecks detected. Use the Profile tab to profile components.</div>
          ) : (
            <div className="forge-skill-list">
              {bottlenecks.map((b, idx) => (
                <div key={idx} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{b.component_id}</div>
                    <span className="dashboard-badge" style={{
                      background: severityColors[b.severity] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {b.severity}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Type: {b.type}</div>
                    <div>Current Value: {b.current_value} | Threshold: {b.threshold}</div>
                    <div>Impact: {b.impact}</div>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <button
                      className="btn-primary"
                      onClick={() => handleRecommend(b.component_id)}
                      disabled={recommending === b.component_id}
                      style={{ background: '#8b5cf6' }}
                    >
                      {recommending === b.component_id ? 'Generating...' : 'Recommend'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Tune Section ── */}
      {activeTab === 'tune' && (
        <div className="dashboard-section">
          <h3>Auto Tune Component</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Component ID</label>
              <input
                type="text"
                value={tuneComponentId}
                onChange={e => setTuneComponentId(e.target.value)}
                placeholder="Enter component ID to auto-tune..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleAutoTune}
              disabled={tuning || !tuneComponentId.trim()}
              style={{ background: '#06b6d4' }}
            >
              {tuning ? 'Auto Tuning...' : 'Auto Tune'}
            </button>
          </div>

          {tuningResult && (
            <div className="dashboard-section">
              <h3>Tuning Result: {tuningResult.component_id}</h3>
              <div className="dashboard-stat-row">
                <span>Overall Improvement</span>
                <strong style={{ color: tuningResult.overall_improvement > 0 ? '#22c55e' : '#f59e0b' }}>
                  {tuningResult.overall_improvement.toFixed(1)}%
                </strong>
              </div>
              {tuningResult.optimizations_applied.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Optimizations Applied</h4>
                  <div className="forge-skill-list">
                    {tuningResult.optimizations_applied.map((opt, idx) => (
                      <div key={idx} className="forge-skill-card">
                        <div className="forge-skill-meta">{opt}</div>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {tuningResult.recommendations.length > 0 && (
                <>
                  <h4 style={{ marginTop: 16 }}>Recommendations</h4>
                  <div className="forge-skill-list">
                    {tuningResult.recommendations.map((rec, idx) => (
                      <div key={idx} className="forge-skill-card">
                        <div className="forge-skill-meta">{rec}</div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Report Section ── */}
      {activeTab === 'report' && (
        <div className="dashboard-section">
          <h3>Comprehensive Performance Report</h3>
          {reportLoading ? (
            <div className="panel-loading">
              <div className="spinner" />
              <span>Loading report...</span>
            </div>
          ) : report ? (
            <>
              <div className="dashboard-stat-row">
                <span>Overall Improvement</span>
                <strong style={{ color: report.overall_improvement > 0 ? '#22c55e' : '#f59e0b' }}>
                  {report.overall_improvement.toFixed(1)}%
                </strong>
              </div>

              <h4 style={{ marginTop: 24 }}>Components ({report.components?.length || 0})</h4>
              {report.components && report.components.length > 0 ? (
                <div className="forge-skill-list">
                  {report.components.map((comp, idx) => (
                    <div key={idx} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{comp.component_id}</div>
                        <span className="dashboard-badge" style={{ background: '#3b82f6', color: '#fff' }}>
                          {comp.component_type}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Avg Latency: {comp.avg_latency_ms.toFixed(2)}ms | P95: {comp.p95_latency_ms.toFixed(2)}ms | P99: {comp.p99_latency_ms.toFixed(2)}ms</div>
                        <div>Throughput: {comp.throughput.toFixed(2)} req/s | Error Rate: {(comp.error_rate * 100).toFixed(2)}%</div>
                        <div>Cache Hit Rate: {(comp.cache_hit_rate * 100).toFixed(1)}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No components in report</div>
              )}

              <h4 style={{ marginTop: 24 }}>Bottlenecks ({report.bottlenecks?.length || 0})</h4>
              {report.bottlenecks && report.bottlenecks.length > 0 ? (
                <div className="forge-skill-list">
                  {report.bottlenecks.map((b, idx) => (
                    <div key={idx} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{b.component_id}</div>
                        <span className="dashboard-badge" style={{
                          background: severityColors[b.severity] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {b.severity}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Type: {b.type} | Current: {b.current_value} | Threshold: {b.threshold}</div>
                        <div>Impact: {b.impact}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No bottlenecks in report</div>
              )}

              <h4 style={{ marginTop: 24 }}>Optimizations ({report.optimizations?.length || 0})</h4>
              {report.optimizations && report.optimizations.length > 0 ? (
                <div className="forge-skill-list">
                  {report.optimizations.map((opt, idx) => (
                    <div key={idx} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{opt.component_id}</div>
                        <span className="dashboard-badge" style={{
                          background: opt.overall_improvement > 0 ? '#22c55e' : '#f59e0b',
                          color: '#fff',
                        }}>
                          {opt.overall_improvement.toFixed(1)}%
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Applied: {opt.optimizations_applied?.join(', ') || 'None'}</div>
                        <div>Recommendations: {opt.recommendations?.join('; ') || 'None'}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No optimizations in report</div>
              )}
            </>
          ) : (
            <div className="panel-empty">Failed to load report. Try again.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default PerformanceAutotunerPanel;