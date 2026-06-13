import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { Agent } from '../types';

interface EvolutionStats {
  agent_id: string;
  total_experiences: number;
  buffer_size: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  pathways_count: number;
  insights_count: number;
  last_analysis_at: string;
  analysis_threshold: number;
}

interface EvolutionPathway {
  id: string;
  name: string;
  task_pattern: string;
  recommended_strategy: string;
  success_rate: number;
  sample_count: number;
  avg_tokens: number;
  avg_latency_ms: number;
  confidence: number;
  last_updated: string;
}

interface EvolutionPanelProps {
  agent: Agent;
}

export const EvolutionPanel: React.FC<EvolutionPanelProps> = ({ agent }) => {
  const [stats, setStats] = useState<EvolutionStats | null>(null);
  const [pathways, setPathways] = useState<EvolutionPathway[]>([]);
  const [insights, setInsights] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'pathways' | 'insights'>('overview');
  const [runningCycle, setRunningCycle] = useState(false);
  const { success: showSuccess, error: showError } = useToast();

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, pathwaysRes, insightsRes] = await Promise.all([
        api.evolution.stats(agent.id),
        api.evolution.pathways(agent.id),
        api.evolution.insights(agent.id),
      ]);
      setStats(statsRes as EvolutionStats);
      setPathways(pathwaysRes.pathways || []);
      setInsights(insightsRes.insights || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load evolution data');
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunCycle = async () => {
    try {
      setRunningCycle(true);
      const result = await api.evolution.runCycle(agent.id);
      showSuccess(`Evolution cycle completed: ${result.pathways_discovered || 0} pathways discovered`);
      await loadData();
    } catch (e: any) {
      showError(e.message || 'Failed to run evolution cycle');
    } finally {
      setRunningCycle(false);
    }
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Evolution</h2>
        </div>
        <div className="panel-content">
          <div className="empty-state">Loading evolution data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Evolution</h2>
        </div>
        <div className="panel-content">
          <div className="empty-state" style={{ color: 'var(--red)' }}>{error}</div>
          <button className="btn-secondary" onClick={loadData}>Retry</button>
        </div>
      </div>
    );
  }

  const strategyLabels: Record<string, string> = {
    direct: 'Direct',
    reasoned: 'Reasoned',
    exploratory: 'Exploratory',
    plan_driven: 'Plan-Driven',
    verified: 'Verified',
    delegated: 'Delegated',
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Evolution</h2>
        <div className="panel-header-actions">
          <button
            className="btn-primary"
            onClick={handleRunCycle}
            disabled={runningCycle}
          >
            {runningCycle ? 'Running...' : 'Run Cycle'}
          </button>
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
          className={`panel-tab ${activeTab === 'pathways' ? 'active' : ''}`}
          onClick={() => setActiveTab('pathways')}
        >
          Pathways ({pathways.length})
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
          <div className="evolution-overview">
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-value">{stats.total_experiences}</div>
                <div className="metric-label">Total Experiences</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{(stats.success_rate * 100).toFixed(1)}%</div>
                <div className="metric-label">Success Rate</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{stats.pathways_count}</div>
                <div className="metric-label">Pathways</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{stats.buffer_size}/{stats.analysis_threshold}</div>
                <div className="metric-label">Buffer / Threshold</div>
              </div>
            </div>

            <div className="evolution-progress-section">
              <h3>Experience Buffer</h3>
              <div className="progress-bar-container">
                <div className="progress-bar-label">
                  {stats.buffer_size} / {stats.analysis_threshold}
                </div>
                <div className="progress-bar-track">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${Math.min(100, (stats.buffer_size / stats.analysis_threshold) * 100)}%`,
                    }}
                  />
                </div>
              </div>
              <div className="progress-bar-hint">
                {stats.buffer_size >= stats.analysis_threshold
                  ? 'Threshold reached — analysis will run automatically'
                  : `${stats.analysis_threshold - stats.buffer_size} more experiences needed for next analysis`}
              </div>
            </div>

            <div className="evolution-breakdown">
              <div className="evolution-stat-row">
                <span className="evolution-stat-label">Successes</span>
                <span className="evolution-stat-value success">{stats.success_count}</span>
              </div>
              <div className="evolution-stat-row">
                <span className="evolution-stat-label">Failures</span>
                <span className="evolution-stat-value failure">{stats.failure_count}</span>
              </div>
              <div className="evolution-stat-row">
                <span className="evolution-stat-label">Last Analysis</span>
                <span className="evolution-stat-value">
                  {stats.last_analysis_at
                    ? new Date(stats.last_analysis_at).toLocaleString()
                    : 'Never'}
                </span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'pathways' && (
          <div className="evolution-pathways">
            {pathways.length === 0 ? (
              <div className="empty-state">
                No optimization pathways discovered yet. Run an evolution cycle to analyze experiences.
              </div>
            ) : (
              pathways.map((p) => (
                <div key={p.id} className="pathway-card">
                  <div className="pathway-header">
                    <span className="pathway-name">{p.name}</span>
                    <span className={`pathway-confidence ${p.confidence >= 0.7 ? 'high' : p.confidence >= 0.4 ? 'medium' : 'low'}`}>
                      {(p.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                  <div className="pathway-details">
                    <div className="pathway-detail-item">
                      <span className="pathway-detail-label">Strategy</span>
                      <span className="pathway-detail-value strategy">
                        {strategyLabels[p.recommended_strategy] || p.recommended_strategy}
                      </span>
                    </div>
                    <div className="pathway-detail-item">
                      <span className="pathway-detail-label">Success Rate</span>
                      <span className="pathway-detail-value">{(p.success_rate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="pathway-detail-item">
                      <span className="pathway-detail-label">Samples</span>
                      <span className="pathway-detail-value">{p.sample_count}</span>
                    </div>
                    <div className="pathway-detail-item">
                      <span className="pathway-detail-label">Avg Tokens</span>
                      <span className="pathway-detail-value">{p.avg_tokens}</span>
                    </div>
                    <div className="pathway-detail-item">
                      <span className="pathway-detail-label">Avg Latency</span>
                      <span className="pathway-detail-value">{p.avg_latency_ms.toFixed(0)}ms</span>
                    </div>
                  </div>
                  <div className="pathway-pattern">
                    <span className="pathway-pattern-label">Pattern:</span>
                    <code className="pathway-pattern-value">{p.task_pattern}</code>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'insights' && (
          <div className="evolution-insights">
            {insights.length === 0 ? (
              <div className="empty-state">
                No evolution insights yet. Run an evolution cycle to generate optimization insights.
              </div>
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