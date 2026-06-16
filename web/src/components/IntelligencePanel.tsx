import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { IntelligenceStats, IntelligenceAnalysis, LearningInsights, Experience } from '../types';

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
  const [activeSection, setActiveSection] = useState<'overview' | 'analyze' | 'plan' | 'tools'>('overview');

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

  if (loading) return <div className="panel-loading">Loading intelligence data...</div>;

  return (
    <div className="intelligence-panel">
      <div className="panel-header">
        <h2>Agent Intelligence</h2>
        <button onClick={loadData} className="btn btn-sm btn-primary">Refresh</button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="section-tabs">
        {(['overview', 'analyze', 'plan', 'tools'] as const).map((s) => (
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
    </div>
  );
};