import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface BrainCycle {
  cycle_id: string;
  mode: string;
  success: boolean;
  duration_ms: number;
  tokens: number;
}

interface BrainStats {
  total_cycles: number;
  successful_cycles: number;
  failed_cycles: number;
  success_rate: number;
  total_tokens: number;
  total_time_ms: number;
  avg_cycle_time_ms: number;
  recent_cycles: BrainCycle[];
  mode_distribution: Record<string, number>;
  uptime_since: string;
}

interface PerceptionHistory {
  perception_id: string;
  intent: string;
  complexity: number;
  urgency: number;
  suggested_mode: string;
  keywords: string[];
  timestamp: string;
}

export function UnifiedBrainPanel() {
  const [stats, setStats] = useState<BrainStats | null>(null);
  const [perceptions, setPerceptions] = useState<PerceptionHistory[]>([]);
  const [insights, setInsights] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testInput, setTestInput] = useState('');
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, perceptionsRes, insightsRes] = await Promise.all([
        api.brain.stats(),
        api.brain.perceptions(),
        api.brain.insights(),
      ]);
      setStats(statsRes);
      setPerceptions(perceptionsRes.perceptions || []);
      setInsights(insightsRes.insights || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load brain data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTest = async () => {
    if (!testInput.trim()) return;
    try {
      setTestLoading(true);
      setTestResult(null);
      const result = await api.brain.process({
        message: testInput,
        agent_id: 'test-agent',
        agent_name: 'Test Agent',
        mode: 'deliberative',
      });
      setTestResult(JSON.stringify(result, null, 2));
    } catch (err) {
      setTestResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setTestLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header"><h2>Unified Brain</h2></div>
        <div className="panel-body"><div className="loading-spinner">Loading...</div></div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Unified Brain</h2>
        <span className="panel-badge">Perceive-Think-Act-Reflect</span>
      </div>
      <div className="panel-body">
        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {/* Stats Overview */}
        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_cycles}</div>
              <div className="stat-label">Total Cycles</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{Math.round(stats.success_rate * 100)}%</div>
              <div className="stat-label">Success Rate</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.avg_cycle_time_ms.toFixed(0)}ms</div>
              <div className="stat-label">Avg Cycle Time</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_tokens.toLocaleString()}</div>
              <div className="stat-label">Total Tokens</div>
            </div>
          </div>
        )}

        {/* Mode Distribution */}
        {stats && stats.mode_distribution && (
          <div className="section">
            <h3>Mode Distribution</h3>
            <div className="mode-bars">
              {Object.entries(stats.mode_distribution).map(([mode, count]) => (
                <div key={mode} className="mode-bar-item">
                  <div className="mode-bar-label">{mode}</div>
                  <div className="mode-bar-track">
                    <div
                      className="mode-bar-fill"
                      style={{
                        width: `${(count / (stats.total_cycles || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <div className="mode-bar-count">{count}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Cycles */}
        {stats && stats.recent_cycles && stats.recent_cycles.length > 0 && (
          <div className="section">
            <h3>Recent Cycles</h3>
            <div className="cycle-list">
              {stats.recent_cycles.map((cycle) => (
                <div key={cycle.cycle_id} className={`cycle-item ${cycle.success ? 'success' : 'failed'}`}>
                  <span className="cycle-mode">{cycle.mode}</span>
                  <span className="cycle-duration">{cycle.duration_ms.toFixed(0)}ms</span>
                  <span className="cycle-tokens">{cycle.tokens} tokens</span>
                  <span className={`cycle-status ${cycle.success ? 'success' : 'failed'}`}>
                    {cycle.success ? 'OK' : 'FAIL'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Perception History */}
        {perceptions.length > 0 && (
          <div className="section">
            <h3>Perception History</h3>
            <div className="perception-list">
              {perceptions.slice(0, 10).map((p) => (
                <div key={p.perception_id} className="perception-item">
                  <div className="perception-header">
                    <span className="perception-intent">{p.intent}</span>
                    <span className="perception-mode">{p.suggested_mode}</span>
                  </div>
                  <div className="perception-metrics">
                    <span>Complexity: {p.complexity.toFixed(2)}</span>
                    <span>Urgency: {p.urgency.toFixed(2)}</span>
                  </div>
                  <div className="perception-keywords">
                    {p.keywords.map((kw) => (
                      <span key={kw} className="keyword-tag">{kw}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Insights */}
        {insights.length > 0 && (
          <div className="section">
            <h3>Brain Insights</h3>
            <ul className="insights-list">
              {insights.map((insight, i) => (
                <li key={i} className="insight-item">{insight}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Test Section */}
        <div className="section">
          <h3>Test Unified Brain</h3>
          <div className="test-form">
            <textarea
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              placeholder="Enter a message to test the unified brain..."
              rows={3}
              className="test-input"
            />
            <button
              onClick={handleTest}
              disabled={testLoading || !testInput.trim()}
              className="btn-primary"
            >
              {testLoading ? 'Processing...' : 'Process with Unified Brain'}
            </button>
          </div>
          {testResult && (
            <pre className="test-result">{testResult}</pre>
          )}
        </div>
      </div>

      <style>{`
        .panel { height: 100%; display: flex; flex-direction: column; overflow: hidden; }
        .panel-header { display: flex; align-items: center; gap: 12px; padding: 16px 20px; border-bottom: 1px solid var(--border); }
        .panel-header h2 { margin: 0; font-size: 18px; }
        .panel-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--accent); color: #fff; }
        .panel-body { flex: 1; overflow-y: auto; padding: 20px; }
        .error-banner { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; margin-bottom: 16px; color: #b91c1c; }
        .error-banner button { background: none; border: none; color: #b91c1c; cursor: pointer; font-weight: 600; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .stat-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: 700; color: var(--accent); }
        .stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
        .section { margin-bottom: 24px; }
        .section h3 { font-size: 14px; margin-bottom: 12px; color: var(--text-secondary); }
        .mode-bars { display: flex; flex-direction: column; gap: 8px; }
        .mode-bar-item { display: flex; align-items: center; gap: 10px; }
        .mode-bar-label { width: 100px; font-size: 12px; text-transform: capitalize; }
        .mode-bar-track { flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
        .mode-bar-fill { height: 100%; background: var(--accent); border-radius: 4px; transition: width 0.3s; }
        .mode-bar-count { width: 40px; text-align: right; font-size: 12px; color: var(--text-secondary); }
        .cycle-list { display: flex; flex-direction: column; gap: 6px; }
        .cycle-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; font-size: 13px; }
        .cycle-item.success { border-left: 3px solid #22c55e; }
        .cycle-item.failed { border-left: 3px solid #ef4444; }
        .cycle-mode { text-transform: capitalize; font-weight: 600; min-width: 90px; }
        .cycle-duration, .cycle-tokens { color: var(--text-secondary); }
        .cycle-status { margin-left: auto; font-size: 11px; padding: 2px 6px; border-radius: 4px; }
        .cycle-status.success { background: #dcfce7; color: #166534; }
        .cycle-status.failed { background: #fef2f2; color: #991b1b; }
        .perception-list { display: flex; flex-direction: column; gap: 8px; }
        .perception-item { padding: 10px 12px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; }
        .perception-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
        .perception-intent { font-weight: 600; text-transform: capitalize; }
        .perception-mode { font-size: 11px; padding: 1px 6px; background: var(--accent); color: #fff; border-radius: 4px; }
        .perception-metrics { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
        .perception-keywords { display: flex; gap: 4px; flex-wrap: wrap; }
        .keyword-tag { font-size: 11px; padding: 1px 6px; background: var(--border); border-radius: 4px; }
        .insights-list { padding-left: 20px; }
        .insight-item { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; }
        .test-form { display: flex; flex-direction: column; gap: 10px; }
        .test-input { width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--card-bg); color: var(--text); resize: vertical; font-family: inherit; }
        .test-result { margin-top: 12px; padding: 12px; background: #1e1e1e; color: #d4d4d4; border-radius: 6px; font-size: 12px; overflow-x: auto; max-height: 300px; overflow-y: auto; }
        .btn-primary { padding: 8px 16px; background: var(--accent); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
        .loading-spinner { text-align: center; padding: 40px; color: var(--text-secondary); }
      `}</style>
    </div>
  );
}