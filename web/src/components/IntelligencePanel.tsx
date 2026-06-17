import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type {
  IntelligenceStats, IntelligenceAnalysis, LearningInsights, Experience,
  StrategyDispatch, ToolEffectiveness, LessonLearned, UncertaintyGaugeData, PromptAnalysis,
} from '../types';

export const IntelligencePanel: React.FC = () => {
  const [stats, setStats] = useState<IntelligenceStats | null>(null);
  const [insights, setInsights] = useState<LearningInsights | null>(null);
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [analysis, setAnalysis] = useState<IntelligenceAnalysis | null>(null);
  const [toolSequence, setToolSequence] = useState<string[][]>([]);
  const [selectedTools, setSelectedTools] = useState<Array<{ name: string; description: string }>>([]);
  const [analysisPrompt, setAnalysisPrompt] = useState('');
  const [sequenceTask, setSequenceTask] = useState('');
  const [toolPrompt, setToolPrompt] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'analyze' | 'plan' | 'tools' | 'strategy-viz' | 'tool-effectiveness' | 'lessons' | 'uncertainty' | 'prompt-analyzer'>('overview');

  // Strategy visualization state
  const [strategies, setStrategies] = useState<StrategyDispatch[]>([]);

  // Tool effectiveness state
  const [toolEffectiveness, setToolEffectiveness] = useState<ToolEffectiveness[]>([]);

  // Lessons learned state
  const [lessons, setLessons] = useState<LessonLearned[]>([]);

  // Uncertainty gauge state
  const [uncertaintyResponseId, setUncertaintyResponseId] = useState('');
  const [uncertaintyGauge, setUncertaintyGauge] = useState<UncertaintyGaugeData | null>(null);
  const [uncertaintyLoading, setUncertaintyLoading] = useState(false);

  // Prompt analyzer state
  const [promptToAnalyze, setPromptToAnalyze] = useState('');
  const [promptAnalysis, setPromptAnalysis] = useState<PromptAnalysis | null>(null);
  const [promptAnalyzerLoading, setPromptAnalyzerLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, i, e] = await Promise.all([
        api.intelligence.stats(),
        api.intelligence.insights(),
        api.intelligence.experiences(20),
      ]);
      setStats(s);
      setInsights(i);
      setExperiences(e.experiences);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load intelligence data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAnalyze = async () => {
    if (!analysisPrompt.trim()) return;
    try {
      const result = await api.intelligence.analyze(analysisPrompt);
      setAnalysis(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    }
  };

  const handlePlanTools = async () => {
    if (!sequenceTask.trim()) return;
    try {
      const result = await api.intelligence.planTools(sequenceTask);
      setToolSequence(result.sequence);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Tool planning failed');
    }
  };

  const handleSelectTools = async () => {
    if (!toolPrompt.trim()) return;
    try {
      const result = await api.intelligence.selectTools(toolPrompt, 10);
      setSelectedTools(result.tools);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Tool selection failed');
    }
  };

  const loadStrategies = async () => {
    try {
      const result = await api.intelligence.strategyDispatch();
      setStrategies(result.strategies);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load strategies');
    }
  };

  const loadToolEffectiveness = async () => {
    try {
      const result = await api.intelligence.toolEffectiveness();
      setToolEffectiveness(result.tools);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load tool effectiveness');
    }
  };

  const loadLessons = async () => {
    try {
      const result = await api.intelligence.lessonsLearned(30);
      setLessons(result.lessons);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load lessons');
    }
  };

  const handleUncertainty = async () => {
    if (!uncertaintyResponseId.trim()) return;
    setUncertaintyLoading(true);
    try {
      const result = await api.intelligence.uncertaintyGauge(uncertaintyResponseId);
      setUncertaintyGauge(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Uncertainty check failed');
    } finally {
      setUncertaintyLoading(false);
    }
  };

  const handlePromptAnalyze = async () => {
    if (!promptToAnalyze.trim()) return;
    setPromptAnalyzerLoading(true);
    try {
      const result = await api.intelligence.promptAnalyzer(promptToAnalyze);
      setPromptAnalysis(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Prompt analysis failed');
    } finally {
      setPromptAnalyzerLoading(false);
    }
  };

  if (loading) return <div className="panel-loading">Loading intelligence data...</div>;

  const maxStrategyUsage = strategies.length > 0 ? Math.max(...strategies.map((s) => s.usage_count), 1) : 1;

  return (
    <div className="intelligence-panel">
      <div className="panel-header">
        <h2>Agent Intelligence</h2>
        <button onClick={loadData} className="btn btn-sm btn-primary">Refresh</button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="section-tabs">
        {(['overview', 'analyze', 'plan', 'tools', 'strategy-viz', 'tool-effectiveness', 'lessons', 'uncertainty', 'prompt-analyzer'] as const).map((s) => (
          <button
            key={s}
            className={`tab-btn ${activeSection === s ? 'active' : ''}`}
            onClick={() => {
              setActiveSection(s);
              if (s === 'strategy-viz' && strategies.length === 0) loadStrategies();
              if (s === 'tool-effectiveness' && toolEffectiveness.length === 0) loadToolEffectiveness();
              if (s === 'lessons' && lessons.length === 0) loadLessons();
            }}
          >
            {s === 'strategy-viz' ? 'Strategies' : s === 'tool-effectiveness' ? 'Tool Effectiveness' : s === 'lessons' ? 'Lessons' : s === 'uncertainty' ? 'Uncertainty' : s === 'prompt-analyzer' ? 'Prompt Analyzer' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {activeSection === 'overview' && stats && (
        <div className="intelligence-overview">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total Experiences</div>
              <div className="stat-value">{stats.total_experiences}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Success Rate</div>
              <div className="stat-value">{(stats.success_rate * 100).toFixed(1)}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Active Traces</div>
              <div className="stat-value">{stats.active_traces}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Tools Tracked</div>
              <div className="stat-value">{stats.tools_tracked}</div>
            </div>
          </div>

          {insights && (
            <div className="learning-insights">
              <h3>Learning Insights</h3>
              {insights.overall_success_rate !== undefined && (
                <div className="insight-stat">
                  <label>Overall Success Rate</label>
                  <span>{(insights.overall_success_rate * 100).toFixed(1)}%</span>
                </div>
              )}
              {insights.recent_lessons && insights.recent_lessons.length > 0 && (
                <div className="recent-lessons">
                  <h4>Recent Lessons</h4>
                  <ul>
                    {insights.recent_lessons.map((lesson, i) => (
                      <li key={i}>{lesson}</li>
                    ))}
                  </ul>
                </div>
              )}
              {insights.strategy_effectiveness && Object.keys(insights.strategy_effectiveness).length > 0 && (
                <div className="strategy-effectiveness">
                  <h4>Strategy Effectiveness</h4>
                  <div className="table-container">
                    <table>
                      <thead>
                        <tr>
                          <th>Strategy</th>
                          <th>Success Rate</th>
                          <th>Attempts</th>
                          <th>Avg Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(insights.strategy_effectiveness).map(([name, data]) => (
                          <tr key={name}>
                            <td>{name}</td>
                            <td>{(data.success_rate * 100).toFixed(1)}%</td>
                            <td>{data.attempts}</td>
                            <td>{data.avg_duration.toFixed(1)}ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {experiences.length > 0 && (
            <div className="recent-experiences">
              <h3>Recent Experiences</h3>
              <div className="experiences-list">
                {experiences.map((exp, i) => (
                  <div key={i} className="experience-card">
                    <div className="exp-header">
                      <span className="badge">{exp.pattern}</span>
                      <span className={`badge ${exp.outcome === 'success' ? 'badge-success' : exp.outcome === 'partial' ? 'badge-warning' : 'badge-error'}`}>{exp.outcome}</span>
                    </div>
                    <p className="exp-strategy">Strategy: {exp.strategy}</p>
                    {exp.lessons.length > 0 && (
                      <p className="exp-lessons">{exp.lessons.join('; ')}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'analyze' && (
        <div className="analyze-section">
          <h3>Task Analysis</h3>
          <div className="analysis-form">
            <input
              type="text"
              value={analysisPrompt}
              onChange={(e) => setAnalysisPrompt(e.target.value)}
              placeholder="Enter a task to analyze (e.g., 'explain how to debug python code')"
              className="input"
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
            />
            <button onClick={handleAnalyze} className="btn btn-primary">Analyze</button>
          </div>
          {analysis && (
            <div className="analysis-result">
              <div className="analysis-grid">
                <div className="analysis-item">
                  <label>Complexity</label>
                  <span className={`badge badge-${analysis.complexity}`}>{analysis.complexity}</span>
                </div>
                <div className="analysis-item">
                  <label>Strategy</label>
                  <span className="badge badge-primary">{analysis.recommended_strategy}</span>
                </div>
                <div className="analysis-item">
                  <label>Mode</label>
                  <span className="badge">{analysis.mode}</span>
                </div>
                <div className="analysis-item">
                  <label>Estimated Steps</label>
                  <span>{analysis.estimated_steps}</span>
                </div>
              </div>
              <div className="relevant-tools">
                <h4>Relevant Tools</h4>
                {analysis.relevant_tools.map((t) => (
                  <div key={t.name} className="tool-item">
                    <span className="tool-name">{t.name}</span>
                    <span className="tool-score">Score: {(t.score * 100).toFixed(0)}%</span>
                    <span className="tool-reason">{t.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'plan' && (
        <div className="plan-section">
          <h3>Tool Sequence Planning</h3>
          <div className="analysis-form">
            <input
              type="text"
              value={sequenceTask}
              onChange={(e) => setSequenceTask(e.target.value)}
              placeholder="Enter a task (e.g., 'research AI trends')"
              className="input"
              onKeyDown={(e) => e.key === 'Enter' && handlePlanTools()}
            />
            <button onClick={handlePlanTools} className="btn btn-primary">Plan Sequence</button>
          </div>
          {toolSequence.length > 0 && (
            <div className="sequence-result">
              <h4>Execution Sequence</h4>
              <div className="sequence-steps">
                {toolSequence.map((step, i) => (
                  <div key={i} className="sequence-step">
                    <div className="step-number">Step {i + 1}</div>
                    <div className="step-tools">
                      {step.map((tool, j) => (
                        <span key={j} className="badge badge-primary">{tool}</span>
                      ))}
                      {step.length > 1 && <span className="parallel-badge">parallel</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'tools' && (
        <div className="tools-section">
          <h3>Intelligent Tool Selection</h3>
          <div className="analysis-form">
            <input
              type="text"
              value={toolPrompt}
              onChange={(e) => setToolPrompt(e.target.value)}
              placeholder="Enter a task (e.g., 'debug python code')"
              className="input"
              onKeyDown={(e) => e.key === 'Enter' && handleSelectTools()}
            />
            <button onClick={handleSelectTools} className="btn btn-primary">Select Tools</button>
          </div>
          {selectedTools.length > 0 && (
            <div className="tools-result">
              <h4>Selected Tools ({selectedTools.length})</h4>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Tool</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTools.map((t) => (
                      <tr key={t.name}>
                        <td><span className="badge">{t.name}</span></td>
                        <td>{t.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'strategy-viz' && (
        <div className="strategy-viz-section">
          <h3>Strategy Dispatch</h3>
          <p className="section-description">Usage and success rates across reasoning strategies.</p>
          {strategies.length === 0 ? (
            <div className="empty-state-with-action">
              <p>No strategy data loaded.</p>
              <button onClick={loadStrategies} className="btn btn-primary">Load Strategies</button>
            </div>
          ) : (
            <div className="strategy-chart">
              {strategies.map((s) => (
                <div key={s.strategy} className="strategy-bar-item">
                  <div className="strategy-bar-label">
                    <span className="strategy-name">{s.strategy}</span>
                    <span className="strategy-rate">{(s.success_rate * 100).toFixed(1)}% success</span>
                  </div>
                  <div className="strategy-bar-track">
                    <div
                      className="strategy-bar-fill"
                      style={{
                        width: `${(s.usage_count / maxStrategyUsage) * 100}%`,
                        background: s.success_rate >= 0.8 ? 'var(--green)' : s.success_rate >= 0.5 ? 'var(--amber)' : 'var(--red)',
                      }}
                    />
                  </div>
                  <div className="strategy-bar-meta">
                    <span>{s.usage_count} uses</span>
                    <span>Avg {s.avg_tokens.toLocaleString()} tokens</span>
                    <span>{s.avg_latency_ms.toFixed(0)}ms</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeSection === 'tool-effectiveness' && (
        <div className="tool-effectiveness-section">
          <h3>Tool Effectiveness Heatmap</h3>
          <p className="section-description">Effectiveness of tools across different tasks.</p>
          {toolEffectiveness.length === 0 ? (
            <div className="empty-state-with-action">
              <p>No tool effectiveness data loaded.</p>
              <button onClick={loadToolEffectiveness} className="btn btn-primary">Load Tool Data</button>
            </div>
          ) : (
            <div className="heatmap-container">
              <div className="heatmap-rows">
                {toolEffectiveness.map((tool) => (
                  <div key={tool.tool_name} className="heatmap-row">
                    <div className="tool-name">{tool.tool_name}</div>
                    <div className="heatmap-cells">
                      {[...Array(10)].map((_, i) => {
                        const normalized = Math.min(1, tool.success_rate);
                        return (
                          <div
                            key={i}
                            className="heatmap-cell"
                            style={{
                              background: `rgba(34, 197, 94, ${normalized * (i < Math.round(normalized * 10) ? 1 : 0.15)})`,
                            }}
                            title={`Success rate: ${(tool.success_rate * 100).toFixed(1)}%`}
                          />
                        );
                      })}
                    </div>
                    <div className="tool-metrics">
                      <span>{tool.total_calls} calls</span>
                      <span>{(tool.success_rate * 100).toFixed(1)}% success</span>
                      <span>{tool.avg_duration_ms.toFixed(0)}ms avg</span>
                      <span className={tool.error_rate > 0.1 ? 'text-error' : ''}>{(tool.error_rate * 100).toFixed(1)}% errors</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'lessons' && (
        <div className="lessons-section">
          <h3>Lessons Learned</h3>
          <p className="section-description">Insights extracted from past agent experiences.</p>
          {lessons.length === 0 ? (
            <div className="empty-state-with-action">
              <p>No lessons loaded.</p>
              <button onClick={loadLessons} className="btn btn-primary">Load Lessons</button>
            </div>
          ) : (
            <div className="lessons-feed">
              {lessons.map((lesson) => (
                <div key={lesson.id} className="lesson-card">
                  <div className="lesson-header">
                    <span className={`badge badge-${lesson.impact >= 0.7 ? 'success' : lesson.impact >= 0.4 ? 'warning' : 'info'}`}>
                      {lesson.category}
                    </span>
                    <span className="lesson-impact">Impact: {(lesson.impact * 100).toFixed(0)}%</span>
                  </div>
                  <p className="lesson-content">{lesson.lesson}</p>
                  <div className="lesson-meta">
                    <span className="lesson-source">Source: {lesson.source}</span>
                    <span className="lesson-time">{new Date(lesson.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeSection === 'uncertainty' && (
        <div className="uncertainty-section">
          <h3>Uncertainty Gauge</h3>
          <p className="section-description">Check confidence level of a response.</p>
          <div className="uncertainty-form">
            <input
              type="text"
              placeholder="Response ID"
              value={uncertaintyResponseId}
              onChange={(e) => setUncertaintyResponseId(e.target.value)}
              className="input"
              onKeyDown={(e) => e.key === 'Enter' && handleUncertainty()}
            />
            <button onClick={handleUncertainty} className="btn btn-primary" disabled={uncertaintyLoading || !uncertaintyResponseId.trim()}>
              {uncertaintyLoading ? 'Checking...' : 'Check Uncertainty'}
            </button>
          </div>
          {uncertaintyGauge && (
            <div className="uncertainty-result">
              <div className="uncertainty-gauge-visual">
                <svg width="120" height="120" viewBox="0 0 120 120">
                  <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" strokeWidth="10" />
                  <circle
                    cx="60" cy="60" r="50"
                    fill="none"
                    stroke={uncertaintyGauge.confidence >= 0.7 ? '#22c55e' : uncertaintyGauge.confidence >= 0.4 ? '#f59e0b' : '#ef4444'}
                    strokeWidth="10"
                    strokeDasharray={`${uncertaintyGauge.confidence * 314} 314`}
                    strokeLinecap="round"
                    transform="rotate(-90 60 60)"
                  />
                  <text x="60" y="55" textAnchor="middle" className="gauge-value" fontSize="24" fontWeight="bold">
                    {(uncertaintyGauge.confidence * 100).toFixed(0)}%
                  </text>
                  <text x="60" y="72" textAnchor="middle" className="gauge-label" fontSize="11">
                    {uncertaintyGauge.overall}
                  </text>
                </svg>
              </div>
              <div className="uncertainty-factors">
                <h4>Confidence Factors</h4>
                {uncertaintyGauge.factors.map((f, i) => (
                  <div key={i} className="factor-item">
                    <span className="factor-name">{f.name}</span>
                    <span className={`factor-direction ${f.direction}`}>{f.direction === 'positive' ? '▲' : '▼'}</span>
                    <span className="factor-impact">{(f.impact * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'prompt-analyzer' && (
        <div className="prompt-analyzer-section">
          <h3>Prompt Analyzer</h3>
          <p className="section-description">Analyze and optimize prompt quality.</p>
          <div className="prompt-analyzer-form">
            <textarea
              placeholder="Enter a prompt to analyze..."
              value={promptToAnalyze}
              onChange={(e) => setPromptToAnalyze(e.target.value)}
              className="textarea"
              rows={3}
            />
            <button onClick={handlePromptAnalyze} className="btn btn-primary" disabled={promptAnalyzerLoading || !promptToAnalyze.trim()}>
              {promptAnalyzerLoading ? 'Analyzing...' : 'Analyze Prompt'}
            </button>
          </div>
          {promptAnalysis && (
            <div className="prompt-analysis-result">
              <div className="analysis-stats">
                <div className="stat-card">
                  <div className="stat-label">Complexity</div>
                  <div className="stat-value">{promptAnalysis.complexity}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Clarity Score</div>
                  <div className="stat-value">{(promptAnalysis.clarity_score * 100).toFixed(0)}%</div>
                </div>
              </div>
              {promptAnalysis.suggestions.length > 0 && (
                <div className="prompt-suggestions">
                  <h4>Suggestions</h4>
                  <ul>
                    {promptAnalysis.suggestions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
              {promptAnalysis.optimized_version && (
                <div className="optimized-prompt">
                  <h4>Optimized Version</h4>
                  <div className="optimized-content">{promptAnalysis.optimized_version}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};