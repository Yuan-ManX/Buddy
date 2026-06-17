import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { AgentCoreStats, CoreExecutionTrace, CoreInsight, ProactiveSignal, CoreAnalysis, PipelineRun, StrategyEffectiveness, ExecutionTimelineEntry } from '../types';

export const AgentCorePanel: React.FC = () => {
  const [stats, setStats] = useState<AgentCoreStats | null>(null);
  const [traces, setTraces] = useState<CoreExecutionTrace[]>([]);
  const [insights, setInsights] = useState<CoreInsight[]>([]);
  const [signals, setSignals] = useState<ProactiveSignal[]>([]);
  const [analysis, setAnalysis] = useState<CoreAnalysis | null>(null);
  const [analysisPrompt, setAnalysisPrompt] = useState('');
  const [agentId, setAgentId] = useState('default');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'traces' | 'insights' | 'signals' | 'analysis' | 'pipeline' | 'strategy' | 'timeline'>('overview');

  // Pipeline state
  const [pipelinePrompt, setPipelinePrompt] = useState('');
  const [pipelineRun, setPipelineRun] = useState<PipelineRun | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);

  // Strategy state
  const [strategies, setStrategies] = useState<StrategyEffectiveness[]>([]);

  // Timeline state
  const [timelineEntries, setTimelineEntries] = useState<ExecutionTimelineEntry[]>([]);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, t, i, sig] = await Promise.all([
        api.agentCore.stats(agentId),
        api.agentCore.traces(agentId, 15),
        api.agentCore.insights(agentId, 20),
        api.agentCore.proactiveSignals(agentId, 10),
      ]);
      setStats(s);
      setTraces(t.traces);
      setInsights(i.insights);
      setSignals(sig.signals);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load agent core data');
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  // Real-time polling every 5 seconds
  useEffect(() => {
    loadData();
    pollingRef.current = setInterval(() => {
      loadData();
    }, 5000);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [loadData]);

  // ── Quick Actions ──
  const handleQuickAction = async (action: string) => {
    try {
      switch (action) {
        case 'checkpoint':
          await api.agentCore.checkpoint(agentId);
          loadData();
          break;
        case 'reflect':
          await api.agentCore.reflect(agentId);
          loadData();
          break;
        case 'generateInsights':
          await handleGenerateInsights();
          break;
        case 'refresh':
          loadData();
          break;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : `Action '${action}' failed`);
    }
  };

  // ── Pipeline Runner ──
  const handleRunPipeline = async () => {
    if (!pipelinePrompt.trim()) return;
    try {
      setPipelineLoading(true);
      setPipelineRun(null);
      const result = await api.agentCore.runPipeline(agentId, pipelinePrompt);
      setPipelineRun(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pipeline run failed');
    } finally {
      setPipelineLoading(false);
    }
  };

  const loadStrategyData = useCallback(async () => {
    try {
      const result = await api.agentCore.strategyEffectiveness(agentId);
      setStrategies(result.strategies);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load strategy data');
    }
  }, [agentId]);

  const loadTimelineData = useCallback(async () => {
    try {
      const result = await api.agentCore.timeline(agentId, 15);
      setTimelineEntries(result.entries);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load timeline data');
    }
  }, [agentId]);

  useEffect(() => {
    if (activeSection === 'strategy') loadStrategyData();
    if (activeSection === 'timeline') loadTimelineData();
  }, [activeSection, loadStrategyData, loadTimelineData]);

  const handleAnalyze = async () => {
    if (!analysisPrompt.trim()) return;
    try {
      const result = await api.agentCore.analyze(analysisPrompt, agentId);
      setAnalysis(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    }
  };

  const handleGenerateInsights = async () => {
    try {
      const result = await api.agentCore.generateInsights(agentId);
      setInsights(result.insights);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate insights');
    }
  };

  // Bar chart helper for strategy visualizer
  const maxStrategyRate = Math.max(...strategies.map((s) => s.success_rate), 0);

  if (loading) return <div className="panel-loading">Loading agent core data...</div>;

  return (
    <div className="agent-core-panel">
      <div className="panel-header">
        <h2>Agent Core</h2>
        <div className="agent-id-selector">
          <input
            type="text"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            placeholder="Agent ID"
            className="input-sm"
          />
          <button onClick={loadData} className="btn btn-sm btn-primary">Load</button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Quick Actions Toolbar */}
      <div className="quick-actions-toolbar">
        <button onClick={() => handleQuickAction('checkpoint')} className="btn btn-sm" title="Save checkpoint">Checkpoint</button>
        <button onClick={() => handleQuickAction('reflect')} className="btn btn-sm" title="Run reflection">Reflect</button>
        <button onClick={() => handleQuickAction('generateInsights')} className="btn btn-sm" title="Generate insights">Generate Insights</button>
        <button onClick={() => handleQuickAction('refresh')} className="btn btn-sm btn-primary" title="Refresh data">Refresh</button>
      </div>

      <div className="section-tabs">
        {(['overview', 'traces', 'insights', 'signals', 'analysis', 'pipeline', 'strategy', 'timeline'] as const).map((s) => (
          <button
            key={s}
            className={`tab-btn ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {activeSection === 'overview' && stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">State</div>
            <div className="stat-value">{stats.state}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Executions</div>
            <div className="stat-value">{stats.executions.total}</div>
            <div className="stat-sub">Success: {(stats.executions.success_rate * 100).toFixed(1)}%</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Avg Response</div>
            <div className="stat-value">{stats.performance.avg_response_time_ms.toFixed(0)}ms</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total Tokens</div>
            <div className="stat-value">{stats.performance.total_tokens.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Insights</div>
            <div className="stat-value">{stats.learning.insights}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Proactive Signals</div>
            <div className="stat-value">{stats.proactive_signals}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Checkpoints</div>
            <div className="stat-value">{stats.checkpoints}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Capabilities</div>
            <div className="stat-value-sm">{stats.capabilities.length > 0 ? stats.capabilities.join(', ') : 'None'}</div>
          </div>
        </div>
      )}

      {activeSection === 'traces' && (
        <div className="traces-list">
          <h3>Execution Traces ({traces.length})</h3>
          {traces.length === 0 ? (
            <p className="empty-state">No execution traces recorded yet.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Context</th>
                    <th>Prompt</th>
                    <th>Steps</th>
                    <th>Success</th>
                    <th>Confidence</th>
                    <th>Time</th>
                    <th>Tools</th>
                  </tr>
                </thead>
                <tbody>
                  {traces.map((t) => (
                    <tr key={t.id}>
                      <td><span className="badge">{t.context}</span></td>
                      <td className="truncate">{t.prompt}</td>
                      <td>{t.steps}</td>
                      <td><span className={`badge ${t.success ? 'badge-success' : 'badge-error'}`}>{t.success ? 'Yes' : 'No'}</span></td>
                      <td>{(t.confidence * 100).toFixed(0)}%</td>
                      <td>{t.total_time_ms.toFixed(0)}ms</td>
                      <td>{t.tools_used.join(', ') || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeSection === 'insights' && (
        <div className="insights-section">
          <div className="section-actions">
            <h3>Learned Insights ({insights.length})</h3>
            <button onClick={handleGenerateInsights} className="btn btn-sm btn-primary">Generate Insights</button>
          </div>
          {insights.length === 0 ? (
            <p className="empty-state">No insights learned yet. Run some executions first.</p>
          ) : (
            <div className="insights-grid">
              {insights.map((i) => (
                <div key={i.id} className="insight-card">
                  <div className="insight-header">
                    <span className={`badge badge-${i.category}`}>{i.category}</span>
                    <span className="confidence">{(i.confidence * 100).toFixed(0)}% confidence</span>
                  </div>
                  <p className="insight-content">{i.content}</p>
                  <div className="insight-meta">
                    <span>Evidence: {i.evidence_count}</span>
                    <span>{new Date(i.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeSection === 'signals' && (
        <div className="signals-section">
          <h3>Proactive Signals ({signals.length})</h3>
          {signals.length === 0 ? (
            <p className="empty-state">No proactive signals detected.</p>
          ) : (
            <div className="signals-list">
              {signals.map((s) => (
                <div key={s.id} className="signal-card">
                  <div className="signal-header">
                    <span className={`badge badge-${s.type}`}>{s.type}</span>
                    <span className="priority">Priority: {(s.priority * 100).toFixed(0)}%</span>
                  </div>
                  <p>{s.description}</p>
                  {s.suggested_action && (
                    <p className="suggested-action">Action: {s.suggested_action}</p>
                  )}
                  <span className="timestamp">{new Date(s.timestamp).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeSection === 'analysis' && (
        <div className="analysis-section">
          <h3>Task Analysis</h3>
          <div className="analysis-form">
            <input
              type="text"
              value={analysisPrompt}
              onChange={(e) => setAnalysisPrompt(e.target.value)}
              placeholder="Enter a task prompt to analyze..."
              className="input"
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
            />
            <button onClick={handleAnalyze} className="btn btn-primary">Analyze</button>
          </div>
          {analysis && (
            <div className="analysis-result">
              <div className="analysis-grid">
                <div className="analysis-item">
                  <label>Fingerprint</label>
                  <code>{analysis.fingerprint}</code>
                </div>
                <div className="analysis-item">
                  <label>Strategy</label>
                  <span className="badge badge-primary">{analysis.strategy}</span>
                </div>
                <div className="analysis-item">
                  <label>Source</label>
                  <span className="badge">{analysis.source}</span>
                </div>
                <div className="analysis-item">
                  <label>Confidence</label>
                  <span>{(analysis.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div className="relevant-tools">
                <h4>Relevant Tools</h4>
                <div className="tools-list">
                  {analysis.relevant_tools.map((t) => (
                    <div key={t.tool} className="tool-item">
                      <span className="tool-name">{t.tool}</span>
                      <span className="tool-score">Score: {(t.score * 100).toFixed(0)}%</span>
                      <span className="tool-reason">{t.reason}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Pipeline Runner Section */}
      {activeSection === 'pipeline' && (
        <div className="pipeline-section">
          <h3>Pipeline Runner</h3>
          <p className="section-description">Run the full observe → analyze → plan → execute → reflect pipeline.</p>
          <div className="pipeline-form">
            <textarea
              value={pipelinePrompt}
              onChange={(e) => setPipelinePrompt(e.target.value)}
              placeholder="Enter a task prompt to run through the pipeline..."
              className="textarea"
              rows={3}
            />
            <button onClick={handleRunPipeline} className="btn btn-primary" disabled={pipelineLoading || !pipelinePrompt.trim()}>
              {pipelineLoading ? 'Running...' : 'Run Pipeline'}
            </button>
          </div>

          {pipelineRun && (
            <div className="pipeline-result">
              <div className="pipeline-run-header">
                <span className="pipeline-run-id">Run: {pipelineRun.run_id}</span>
                <span className={`badge badge-${pipelineRun.status === 'completed' ? 'success' : pipelineRun.status === 'failed' ? 'error' : 'warning'}`}>
                  {pipelineRun.status}
                </span>
              </div>
              <div className="pipeline-steps">
                {pipelineRun.steps.map((step, i) => (
                  <div key={i} className={`pipeline-step ${step.status}`}>
                    <div className="pipeline-step-header">
                      <span className={`pipeline-step-dot ${step.status}`} />
                      <span className="pipeline-step-name">{step.step}</span>
                      <span className={`pipeline-step-status ${step.status}`}>{step.status}</span>
                    </div>
                    {step.result && <div className="pipeline-step-result">{step.result}</div>}
                    {step.error && <div className="pipeline-step-error">{step.error}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Strategy Visualizer Section */}
      {activeSection === 'strategy' && (
        <div className="strategy-section">
          <h3>Strategy Visualizer</h3>
          <p className="section-description">Effectiveness of different reasoning strategies.</p>
          {strategies.length === 0 ? (
            <p className="empty-state">No strategy data available. Run some executions first.</p>
          ) : (
            <div className="strategy-chart">
              {strategies.map((s) => (
                <div key={s.strategy} className="strategy-bar-item">
                  <div className="strategy-bar-label">
                    <span className="strategy-name">{s.strategy}</span>
                    <span className="strategy-rate">{(s.success_rate * 100).toFixed(1)}%</span>
                  </div>
                  <div className="strategy-bar-track">
                    <div
                      className="strategy-bar-fill"
                      style={{
                        width: `${(s.success_rate / Math.max(maxStrategyRate, 0.01)) * 100}%`,
                        background: s.success_rate >= 0.8 ? 'var(--green)' : s.success_rate >= 0.5 ? 'var(--amber)' : 'var(--red)',
                      }}
                    />
                  </div>
                  <div className="strategy-bar-meta">
                    <span>{s.attempts} attempts</span>
                    <span>Avg {s.avg_tokens.toLocaleString()} tokens</span>
                    <span>{s.avg_time_ms.toFixed(0)}ms</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Execution Timeline Section */}
      {activeSection === 'timeline' && (
        <div className="execution-timeline-section">
          <h3>Execution Timeline</h3>
          <p className="section-description">Recent execution traces in chronological order.</p>
          {timelineEntries.length === 0 ? (
            <p className="empty-state">No timeline entries. Run some executions first.</p>
          ) : (
            <div className="timeline-view">
              {timelineEntries.map((entry) => (
                <div key={entry.id} className="timeline-item">
                  <div
                    className="timeline-dot"
                    style={{ background: entry.success ? 'var(--green)' : 'var(--red)' }}
                  />
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <span className="timeline-title">{entry.context}</span>
                      <span className="timeline-time">{new Date(entry.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="timeline-desc">{entry.prompt}</div>
                    <div className="timeline-meta">
                      <span className="timeline-badge event">{entry.steps} steps</span>
                      <span className="timeline-badge tool">{(entry.confidence * 100).toFixed(0)}% confidence</span>
                      <span className="timeline-badge task">{entry.total_time_ms.toFixed(0)}ms</span>
                      {entry.tools_used.map((tool) => (
                        <span key={tool} className="timeline-badge tool">{tool}</span>
                      ))}
                    </div>
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