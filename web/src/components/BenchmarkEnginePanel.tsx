import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#9333ea',
  bg: '#faf5ff',
  border: '#e9d5ff',
  text: '#6b21a8',
};

const BENCHMARK_TYPES = ['single_run', 'comparative', 'longitudinal', 'a_b_test', 'regression'];
const METRIC_CATEGORIES = ['accuracy', 'efficiency', 'latency', 'cost', 'quality', 'safety', 'robustness', 'coherence', 'helpfulness', 'creativity'];
const METRIC_SCALES = ['binary', 'percentage', 'rating_5', 'rating_10', 'continuous'];

export const BenchmarkEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'benchmark' | 'evaluate' | 'compare'>('overview');

  // Benchmark list
  const [benchmarks, setBenchmarks] = useState<any[]>([]);

  // Benchmark form
  const [benchmarkForm, setBenchmarkForm] = useState({
    name: '', description: '', benchmark_type: 'single_run',
  });

  // Metrics to register alongside the benchmark
  const [metrics, setMetrics] = useState<any[]>([]);
  const [metricForm, setMetricForm] = useState({
    name: '', category: 'accuracy', scale: 'continuous',
    min_value: '', max_value: '', weight: '',
  });

  // Evaluate form
  const [evaluateForm, setEvaluateForm] = useState({ benchmark_id: '', agent_id: '' });
  const [currentRun, setCurrentRun] = useState<any>(null);
  const [metricResultForm, setMetricResultForm] = useState({ metric_id: '', value: '' });
  const [runScore, setRunScore] = useState<any>(null);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);

  // Compare
  const [compareForm, setCompareForm] = useState({ run_a_id: '', run_b_id: '' });
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  const [leaderboardBenchmarkId, setLeaderboardBenchmarkId] = useState('');
  const [leaderboard, setLeaderboard] = useState<any>(null);

  const loadStats = useCallback(async () => {
    try {
      const s = await api.benchmarkEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load benchmark engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBenchmarks = useCallback(async () => {
    try {
      const result = await api.benchmarkEngine.list();
      setBenchmarks(Array.isArray(result) ? result : (result?.benchmarks ?? []));
    } catch (e: any) {
      // ignore load errors for secondary data
    }
  }, []);

  const loadRecentRuns = useCallback(async () => {
    try {
      const result = await api.benchmarkEngine.listRuns({ limit: 10 });
      setRecentRuns(Array.isArray(result) ? result : (result?.runs ?? []));
    } catch (e: any) {
      // ignore load errors for secondary data
    }
  }, []);

  // Load data on section change
  useEffect(() => {
    loadStats();
    loadBenchmarks();
    if (activeSection === 'evaluate') loadRecentRuns();
  }, [activeSection, loadStats, loadBenchmarks, loadRecentRuns]);

  const handleAddMetric = () => {
    if (!metricForm.name.trim()) return;
    setMetrics(prev => ([
      ...prev,
      {
        name: metricForm.name.trim(),
        category: metricForm.category,
        scale: metricForm.scale,
        min_value: metricForm.min_value !== '' ? Number(metricForm.min_value) : undefined,
        max_value: metricForm.max_value !== '' ? Number(metricForm.max_value) : undefined,
        weight: metricForm.weight !== '' ? Number(metricForm.weight) : undefined,
      },
    ]));
    setMetricForm({ name: '', category: 'accuracy', scale: 'continuous', min_value: '', max_value: '', weight: '' });
  };

  const handleRemoveMetric = (idx: number) => {
    setMetrics(prev => prev.filter((_, i) => i !== idx));
  };

  const handleCreateBenchmark = async () => {
    if (!benchmarkForm.name.trim()) return;
    try {
      setLoading(true);
      await api.benchmarkEngine.create({
        name: benchmarkForm.name.trim(),
        description: benchmarkForm.description.trim() || undefined,
        benchmark_type: benchmarkForm.benchmark_type,
        metric_defs: metrics.length > 0 ? metrics : undefined,
      });
      toast.success(`Benchmark "${benchmarkForm.name}" created`);
      setBenchmarkForm({ name: '', description: '', benchmark_type: 'single_run' });
      setMetrics([]);
      loadStats();
      loadBenchmarks();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartEvaluation = async () => {
    if (!evaluateForm.benchmark_id || !evaluateForm.agent_id.trim()) return;
    try {
      const run = await api.benchmarkEngine.startEvaluation(evaluateForm.benchmark_id, {
        agent_id: evaluateForm.agent_id.trim(),
      });
      setCurrentRun(run);
      setRunScore(null);
      setMetricResultForm({ metric_id: '', value: '' });
      toast.success('Evaluation started');
      loadRecentRuns();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleRecordMetric = async () => {
    if (!currentRun || !metricResultForm.metric_id || metricResultForm.value === '') return;
    try {
      await api.benchmarkEngine.recordMetric(currentRun.id ?? currentRun.run_id, {
        metric_id: metricResultForm.metric_id,
        value: Number(metricResultForm.value),
      });
      toast.success('Metric recorded');
      setMetricResultForm({ metric_id: '', value: '' });
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCompleteEvaluation = async () => {
    if (!currentRun) return;
    const runId = currentRun.id ?? currentRun.run_id;
    try {
      await api.benchmarkEngine.completeEvaluation(runId, {});
      const score = await api.benchmarkEngine.calculateScore(runId);
      setRunScore(score);
      toast.success('Evaluation completed');
      loadRecentRuns();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCompare = async () => {
    if (!compareForm.run_a_id.trim() || !compareForm.run_b_id.trim()) return;
    try {
      const result = await api.benchmarkEngine.compare(compareForm.run_a_id.trim(), compareForm.run_b_id.trim());
      setComparisonResult(result);
      toast.success('Comparison generated');
      loadStats();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleLoadLeaderboard = async () => {
    if (!leaderboardBenchmarkId) return;
    try {
      const result = await api.benchmarkEngine.leaderboard(leaderboardBenchmarkId, 10);
      setLeaderboard(result);
      toast.success('Leaderboard loaded');
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  if (loading && !stats) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>📊 Benchmark Engine</h2>
          <p className="panel-subtitle">Create benchmarks, run evaluations, and compare results</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading benchmark engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>📊 Benchmark Engine</h2>
        <p className="panel-subtitle">Create benchmarks, run evaluations, and compare results</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_benchmarks ?? '-'}</span><span className="stat-label">Benchmarks</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_runs ?? '-'}</span><span className="stat-label">Runs</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.completed_runs ?? '-'}</span><span className="stat-label">Completed</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_score ?? '-'}</span><span className="stat-label">Avg Score</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.comparison_count ?? '-'}</span><span className="stat-label">Comparisons</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'benchmark', 'evaluate', 'compare'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Benchmark Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Benchmarks</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_benchmarks ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Runs</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_runs ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Completed Runs</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.completed_runs ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Score</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_score ?? '-'}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Comparisons</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.comparison_count ?? 0}</div>
              </div>
            </div>

            {stats.benchmarks_by_type && typeof stats.benchmarks_by_type === 'object' && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>Benchmarks by Type</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {Object.entries(stats.benchmarks_by_type).map(([k, v]) => (
                    <span key={k} style={{ padding: '4px 10px', background: '#fff', border: `1px solid ${themeColors.border}`, borderRadius: 12, fontSize: '0.85rem', color: themeColors.text }}>{k}: {String(v)}</span>
                  ))}
                </div>
              </div>
            )}

            {stats.metric_coverage != null && (
              <div style={{ marginTop: 12, fontSize: '0.9rem', color: themeColors.text }}>
                <strong>Metric Coverage:</strong> {String(stats.metric_coverage)}
              </div>
            )}
          </div>

          <h3 style={{ color: themeColors.text }}>Existing Benchmarks</h3>
          {benchmarks.length === 0 ? (
            <div style={{ padding: 16, color: themeColors.text, fontStyle: 'italic' }}>No benchmarks yet. Create one in the Benchmark tab.</div>
          ) : (
            <div style={{ display: 'grid', gap: 8 }}>
              {benchmarks.map((b) => (
                <div key={b.id} style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text }}>{b.name}</div>
                  <div style={{ fontSize: '0.85rem', color: '#666' }}>
                    <span style={{ textTransform: 'capitalize' }}>{b.benchmark_type?.replace(/_/g, ' ')}</span>
                    {b.description ? ` · ${b.description}` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Benchmark */}
      {activeSection === 'benchmark' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Benchmark</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={benchmarkForm.name}
                  onChange={e => setBenchmarkForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Reasoning QA v2"
                />
              </div>
              <div className="form-group">
                <label>Benchmark Type</label>
                <select value={benchmarkForm.benchmark_type} onChange={e => setBenchmarkForm(f => ({ ...f, benchmark_type: e.target.value }))}>
                  {BENCHMARK_TYPES.map(t => (
                    <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={benchmarkForm.description}
                onChange={e => setBenchmarkForm(f => ({ ...f, description: e.target.value }))}
                placeholder="What does this benchmark measure?"
              />
            </div>

            {/* Metrics registration */}
            <div style={{ marginTop: 12, padding: 12, background: themeColors.bg, borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
              <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 8 }}>Register Metrics</div>
              <div className="form-row">
                <div className="form-group">
                  <label>Metric Name *</label>
                  <input
                    type="text"
                    value={metricForm.name}
                    onChange={e => setMetricForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. accuracy"
                  />
                </div>
                <div className="form-group">
                  <label>Category</label>
                  <select value={metricForm.category} onChange={e => setMetricForm(f => ({ ...f, category: e.target.value }))}>
                    {METRIC_CATEGORIES.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Scale</label>
                  <select value={metricForm.scale} onChange={e => setMetricForm(f => ({ ...f, scale: e.target.value }))}>
                    {METRIC_SCALES.map(s => (
                      <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Min Value</label>
                  <input
                    type="number"
                    value={metricForm.min_value}
                    onChange={e => setMetricForm(f => ({ ...f, min_value: e.target.value }))}
                    placeholder="optional"
                  />
                </div>
                <div className="form-group">
                  <label>Max Value</label>
                  <input
                    type="number"
                    value={metricForm.max_value}
                    onChange={e => setMetricForm(f => ({ ...f, max_value: e.target.value }))}
                    placeholder="optional"
                  />
                </div>
                <div className="form-group">
                  <label>Weight</label>
                  <input
                    type="number"
                    step="0.1"
                    value={metricForm.weight}
                    onChange={e => setMetricForm(f => ({ ...f, weight: e.target.value }))}
                    placeholder="e.g. 1.0"
                  />
                </div>
              </div>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary, opacity: !metricForm.name.trim() ? 0.6 : 1 }}
                onClick={handleAddMetric}
                disabled={!metricForm.name.trim()}
              >
                Add Metric
              </button>

              {metrics.length > 0 && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {metrics.map((m, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 10px', background: '#fff', borderRadius: 4, border: `1px solid ${themeColors.border}`, fontSize: '0.85rem' }}>
                      <span style={{ color: themeColors.text }}>
                        <strong>{m.name}</strong> · {m.category} · {m.scale}{m.weight != null ? ` · w=${m.weight}` : ''}
                      </span>
                      <button className="btn-sm" onClick={() => handleRemoveMetric(idx)}>Remove</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              className="btn-primary"
              style={{ background: themeColors.primary, marginTop: 12 }}
              onClick={handleCreateBenchmark}
              disabled={!benchmarkForm.name.trim()}
            >
              Create Benchmark{metrics.length > 0 ? ` with ${metrics.length} metric${metrics.length > 1 ? 's' : ''}` : ''}
            </button>
          </div>
        </div>
      )}

      {/* Evaluate */}
      {activeSection === 'evaluate' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Run Evaluation</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Benchmark *</label>
                <select value={evaluateForm.benchmark_id} onChange={e => setEvaluateForm(f => ({ ...f, benchmark_id: e.target.value }))}>
                  <option value="">Select a benchmark</option>
                  {benchmarks.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  type="text"
                  value={evaluateForm.agent_id}
                  onChange={e => setEvaluateForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="Agent to evaluate"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleStartEvaluation}
              disabled={!evaluateForm.benchmark_id || !evaluateForm.agent_id.trim()}
            >
              Start Evaluation
            </button>
          </div>

          {currentRun && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h4 style={{ color: themeColors.text }}>Active Run: {currentRun.id ?? currentRun.run_id}</h4>
              <div style={{ fontSize: '0.85rem', color: themeColors.text, marginBottom: 12 }}>
                Status: {currentRun.status ?? 'running'} · Benchmark: {currentRun.benchmark_id ?? evaluateForm.benchmark_id}
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Metric ID</label>
                  <input
                    type="text"
                    value={metricResultForm.metric_id}
                    onChange={e => setMetricResultForm(f => ({ ...f, metric_id: e.target.value }))}
                    placeholder="Metric to record"
                  />
                </div>
                <div className="form-group">
                  <label>Value</label>
                  <input
                    type="number"
                    step="any"
                    value={metricResultForm.value}
                    onChange={e => setMetricResultForm(f => ({ ...f, value: e.target.value }))}
                    placeholder="Numeric result"
                  />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn-primary"
                  style={{ background: themeColors.primary }}
                  onClick={handleRecordMetric}
                  disabled={!metricResultForm.metric_id || metricResultForm.value === ''}
                >
                  Record Metric
                </button>
                <button
                  className="btn-primary"
                  style={{ background: themeColors.primary }}
                  onClick={handleCompleteEvaluation}
                >
                  Complete & Score
                </button>
              </div>

              {runScore && (
                <div style={{ marginTop: 12, padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text }}>Run Score</div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(runScore, null, 2)}</pre>
                </div>
              )}
            </div>
          )}

          <h3 style={{ color: themeColors.text }}>Recent Runs</h3>
          {recentRuns.length === 0 ? (
            <div style={{ padding: 16, color: themeColors.text, fontStyle: 'italic' }}>No runs yet.</div>
          ) : (
            <div style={{ display: 'grid', gap: 8 }}>
              {recentRuns.map((r) => (
                <div key={r.id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, fontSize: '0.85rem', color: themeColors.text }}>
                  <strong>{r.id}</strong> · agent: {r.agent_id} · status: {r.status}{r.score != null ? ` · score: ${r.score}` : ''}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Compare */}
      {activeSection === 'compare' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Compare Runs</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Run A ID *</label>
                <input
                  type="text"
                  value={compareForm.run_a_id}
                  onChange={e => setCompareForm(f => ({ ...f, run_a_id: e.target.value }))}
                  placeholder="First run ID"
                />
              </div>
              <div className="form-group">
                <label>Run B ID *</label>
                <input
                  type="text"
                  value={compareForm.run_b_id}
                  onChange={e => setCompareForm(f => ({ ...f, run_b_id: e.target.value }))}
                  placeholder="Second run ID"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCompare}
              disabled={!compareForm.run_a_id.trim() || !compareForm.run_b_id.trim()}
            >
              Compare
            </button>
          </div>

          {comparisonResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h4 style={{ color: themeColors.text }}>Comparison Report</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text }}>Score A</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: themeColors.primary }}>{comparisonResult.score_a ?? '-'}</div>
                </div>
                <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text }}>Score B</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: themeColors.primary }}>{comparisonResult.score_b ?? '-'}</div>
                </div>
              </div>
              {comparisonResult.summary && (
                <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, marginBottom: 12, color: themeColors.text }}>
                  <strong>Summary:</strong> {String(comparisonResult.summary)}
                </div>
              )}
              {comparisonResult.overall_comparison && (
                <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>Overall Comparison</div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(comparisonResult.overall_comparison, null, 2)}</pre>
                </div>
              )}
            </div>
          )}

          <h3 style={{ color: themeColors.text }}>Leaderboard</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Benchmark *</label>
                <select value={leaderboardBenchmarkId} onChange={e => setLeaderboardBenchmarkId(e.target.value)}>
                  <option value="">Select a benchmark</option>
                  {benchmarks.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button
                  className="btn-primary"
                  style={{ background: themeColors.primary }}
                  onClick={handleLoadLeaderboard}
                  disabled={!leaderboardBenchmarkId}
                >
                  Load Leaderboard
                </button>
              </div>
            </div>
          </div>

          {leaderboard && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Leaderboard</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(leaderboard, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BenchmarkEnginePanel;
