import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { Agent } from '../types';

interface MetaCognitionPanelProps {
  agent: Agent;
}

interface StrategyStats {
  agent_id: string;
  total_decisions: number;
  total_outcomes: number;
  success_rate: string;
  recent_successes: number;
  recent_total: number;
  mode_distribution: Record<string, number>;
  avg_estimated_cost: number;
  strategy_stats: Record<string, {
    successes: number;
    failures: number;
    success_rate: string;
    avg_tokens: number;
  }>;
  last_decision_at: string;
}

interface DecisionRecord {
  task_signature: string;
  decision: {
    reasoning_style: string;
    model: string;
    temperature: number;
    execution_mode: string;
    enable_tools: boolean;
    enable_reasoning: boolean;
    context_window_size: number;
    estimated_cost: number;
    confidence: number;
    rationale: string;
  };
  success: boolean;
  quality_score: number;
  actual_tokens: number;
  actual_time_ms: number;
  timestamp: string;
}

export const MetaCognitionPanel: React.FC<MetaCognitionPanelProps> = ({ agent }) => {
  const [stats, setStats] = useState<StrategyStats | null>(null);
  const [insights, setInsights] = useState<string[]>([]);
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'decisions' | 'insights'>('overview');
  const { success: showSuccess, error: showError } = useToast();

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, insightsRes, decisionsRes] = await Promise.all([
        api.metacognition.stats(agent.id),
        api.metacognition.insights(agent.id),
        api.metacognition.decisions(agent.id, 20),
      ]);
      setStats(statsRes as unknown as StrategyStats);
      setInsights(insightsRes.insights || []);
      setDecisions(decisionsRes.decisions || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load metacognition data');
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const modeLabels: Record<string, string> = {
    direct: 'Direct',
    reasoned: 'Reasoned',
    plan_driven: 'Plan-Driven',
    delegated: 'Delegated',
    exploratory: 'Exploratory',
    verified: 'Verified',
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Meta-Cognition</h2>
        </div>
        <div className="panel-loading">Loading strategy data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Meta-Cognition</h2>
        </div>
        <div className="panel-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Meta-Cognition</h2>
        <div className="panel-header-actions">
          <button className="btn-secondary" onClick={loadData}>Refresh</button>
        </div>
      </div>

      <div className="panel-tabs">
        <button
          className={`panel-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`panel-tab ${activeTab === 'decisions' ? 'active' : ''}`}
          onClick={() => setActiveTab('decisions')}
        >
          Decisions ({decisions.length})
        </button>
        <button
          className={`panel-tab ${activeTab === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveTab('insights')}
        >
          Insights ({insights.length})
        </button>
      </div>

      <div className="panel-content">
        {activeTab === 'overview' && stats && (
          <div className="metacognition-overview">
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-value">{stats.total_decisions}</div>
                <div className="metric-label">Total Decisions</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{stats.success_rate}</div>
                <div className="metric-label">Success Rate</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{stats.total_outcomes}</div>
                <div className="metric-label">Outcomes Recorded</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">${stats.avg_estimated_cost.toFixed(4)}</div>
                <div className="metric-label">Avg Cost/Decision</div>
              </div>
            </div>

            <h3>Strategy Distribution</h3>
            <div className="mode-distribution">
              {Object.entries(stats.mode_distribution).map(([mode, count]) => (
                <div key={mode} className="mode-bar-item">
                  <div className="mode-bar-label">{modeLabels[mode] || mode}</div>
                  <div className="mode-bar-track">
                    <div
                      className="mode-bar-fill"
                      style={{
                        width: `${(count / Math.max(...Object.values(stats.mode_distribution), 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <div className="mode-bar-count">{count}</div>
                </div>
              ))}
            </div>

            <h3>Strategy Performance</h3>
            <div className="strategy-stats">
              {Object.entries(stats.strategy_stats).map(([mode, s]) => (
                <div key={mode} className="strategy-card">
                  <div className="strategy-name">{modeLabels[mode] || mode}</div>
                  <div className="strategy-metrics">
                    <span className={`strategy-rate ${parseFloat(s.success_rate) >= 0.7 ? 'good' : parseFloat(s.success_rate) >= 0.4 ? 'warn' : 'bad'}`}>
                      {s.success_rate}
                    </span>
                    <span className="strategy-tokens">{s.avg_tokens} avg tokens</span>
                  </div>
                  <div className="strategy-counts">
                    {s.successes} ✓ / {s.failures} ✗
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'decisions' && (
          <div className="decisions-list">
            {decisions.length === 0 ? (
              <div className="empty-state">No decisions recorded yet. Start chatting to build strategy data.</div>
            ) : (
              decisions.map((d, i) => (
                <div key={i} className={`decision-card ${d.success ? 'success' : 'failure'}`}>
                  <div className="decision-header">
                    <span className="decision-mode">{modeLabels[d.decision.execution_mode] || d.decision.execution_mode}</span>
                    <span className="decision-model">{d.decision.model}</span>
                    <span className={`decision-outcome ${d.success ? 'success' : 'failure'}`}>
                      {d.success ? '✓' : '✗'}
                    </span>
                  </div>
                  <div className="decision-details">
                    <div className="decision-rationale">{d.decision.rationale}</div>
                    <div className="decision-metrics">
                      <span>Quality: {(d.quality_score * 100).toFixed(0)}%</span>
                      <span>Tokens: {d.actual_tokens}</span>
                      <span>Time: {d.actual_time_ms.toFixed(0)}ms</span>
                      <span>Confidence: {(d.decision.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'insights' && (
          <div className="insights-list">
            {insights.length === 0 ? (
              <div className="empty-state">No insights yet. More interactions are needed to generate insights.</div>
            ) : (
              insights.map((insight, i) => (
                <div key={i} className="insight-card">
                  <div className="insight-icon">💡</div>
                  <div className="insight-text">{insight}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};