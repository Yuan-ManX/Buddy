import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface DreamInsight {
  id: string;
  phase: string;
  content: string;
  source_memories: string[];
  confidence: number;
  created_at: string;
}

interface DreamStatus {
  agent_id: string;
  is_running: boolean;
  interval_seconds: number;
  total_insights: number;
  latest_insight: string;
}

interface DreamCycleResult {
  agent_id: string;
  insights: DreamInsight[];
  memories_processed: number;
  memories_consolidated: number;
  duration_seconds: number;
}

interface AgentSimple {
  id: string;
  name: string;
}

export const DreamPanel: React.FC = () => {
  const [agentId, setAgentId] = useState('');
  const [agents, setAgents] = useState<AgentSimple[]>([]);
  const [status, setStatus] = useState<DreamStatus | null>(null);
  const [insights, setInsights] = useState<DreamInsight[]>([]);
  const [lastResult, setLastResult] = useState<DreamCycleResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadAgents();
  }, []);

  useEffect(() => {
    if (agentId) {
      loadDreamData();
    }
  }, [agentId]);

  const loadAgents = async () => {
    try {
      const data = await api.agents.list();
      const list = data.items.map(a => ({ id: a.id, name: a.name }));
      setAgents(list);
      if (list.length > 0) setAgentId(list[0].id);
    } catch {}
  };

  const loadDreamData = async () => {
    if (!agentId) return;
    try {
      const [s, i] = await Promise.all([
        api.dream.status(agentId),
        api.dream.insights(agentId),
      ]);
      setStatus(s);
      setInsights(i);
    } catch (e: any) {
      setError(e.message || 'Failed to load dream data');
    }
  };

  const startDream = async () => {
    setLoading(true);
    setError('');
    try {
      await api.dream.start(agentId);
      await loadDreamData();
    } catch (e: any) {
      setError(e.message || 'Failed to start dream cycle');
    } finally {
      setLoading(false);
    }
  };

  const stopDream = async () => {
    setLoading(true);
    setError('');
    try {
      await api.dream.stop(agentId);
      await loadDreamData();
    } catch (e: any) {
      setError(e.message || 'Failed to stop dream cycle');
    } finally {
      setLoading(false);
    }
  };

  const runOnce = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.dream.run(agentId);
      setLastResult(result);
      await loadDreamData();
    } catch (e: any) {
      setError(e.message || 'Failed to run dream cycle');
    } finally {
      setLoading(false);
    }
  };

  const getPhaseIcon = (phase: string) => {
    const icons: Record<string, string> = {
      review: '🔍', consolidate: '🧩', synthesize: '💡',
      resolve: '🔗', reflect: '🪞',
    };
    return icons[phase] || '✨';
  };

  const getPhaseColor = (phase: string) => {
    const colors: Record<string, string> = {
      review: '#3b82f6', consolidate: '#10b981', synthesize: '#f59e0b',
      resolve: '#ef4444', reflect: '#8b5cf6',
    };
    return colors[phase] || '#6b7280';
  };

  return (
    <div className="dream-panel">
      <h2>Dream Engine</h2>
      <p className="subtitle">Background memory consolidation and creative synthesis</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="dream-agent-select">
        <label>Agent:</label>
        <select value={agentId} onChange={e => setAgentId(e.target.value)}>
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </div>

      {status && (
        <div className="dream-status-card">
          <div className="status-indicator">
            <div className={`status-dot ${status.is_running ? 'running' : 'stopped'}`} />
            <span>{status.is_running ? 'Running' : 'Stopped'}</span>
          </div>
          <div className="status-details">
            <div className="stat-item">
              <span className="stat-label">Interval</span>
              <span className="stat-value">{status.interval_seconds}s</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Total Insights</span>
              <span className="stat-value">{status.total_insights}</span>
            </div>
          </div>
          {status.latest_insight && (
            <div className="latest-insight">
              <span className="label">Latest:</span>
              <span>{status.latest_insight}</span>
            </div>
          )}
          <div className="dream-actions">
            {!status.is_running ? (
              <button className="btn-start" onClick={startDream} disabled={loading}>Start Dream Cycle</button>
            ) : (
              <button className="btn-stop" onClick={stopDream} disabled={loading}>Stop Dream Cycle</button>
            )}
            <button className="btn-run" onClick={runOnce} disabled={loading}>
              {loading ? 'Running...' : 'Run Once'}
            </button>
          </div>
        </div>
      )}

      {lastResult && (
        <div className="dream-run-result">
          <h4>Last Dream Cycle</h4>
          <div className="run-stats">
            <span>Processed: {lastResult.memories_processed} memories</span>
            <span>Consolidated: {lastResult.memories_consolidated}</span>
            <span>Duration: {lastResult.duration_seconds.toFixed(1)}s</span>
            <span>Insights: {lastResult.insights.length}</span>
          </div>
        </div>
      )}

      <div className="dream-insights">
        <h4>Dream Insights ({insights.length})</h4>
        {insights.map(insight => (
          <div key={insight.id} className="insight-card">
            <div className="insight-header">
              <span className="insight-phase" style={{ background: getPhaseColor(insight.phase) }}>
                {getPhaseIcon(insight.phase)} {insight.phase}
              </span>
              <span className="insight-confidence">
                {Math.round(insight.confidence * 100)}% confidence
              </span>
            </div>
            <div className="insight-content">{insight.content}</div>
            {insight.source_memories.length > 0 && (
              <div className="insight-sources">
                Sources: {insight.source_memories.slice(0, 5).join(', ')}
                {insight.source_memories.length > 5 && ` +${insight.source_memories.length - 5} more`}
              </div>
            )}
          </div>
        ))}
        {insights.length === 0 && (
          <div className="empty-state">No dream insights yet. Start a dream cycle to begin processing.</div>
        )}
      </div>

      <style>{`
        .dream-panel { padding: 24px; max-width: 1000px; margin: 0 auto; }
        .dream-panel h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .subtitle { color: #6b7280; margin-bottom: 24px; }
        .dream-agent-select { margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }
        .dream-agent-select label { font-weight: 600; font-size: 0.9rem; }
        .dream-agent-select select { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.9rem; background: #fff; }
        .dream-status-card { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; margin-bottom: 24px; }
        .status-indicator { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; font-weight: 600; }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; }
        .status-dot.running { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.4); animation: pulse 2s infinite; }
        .status-dot.stopped { background: #9ca3af; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
        .status-details { display: flex; gap: 32px; margin-bottom: 16px; }
        .stat-item { display: flex; flex-direction: column; }
        .stat-label { font-size: 0.8rem; color: #6b7280; }
        .stat-value { font-size: 1.2rem; font-weight: 700; }
        .latest-insight { background: #f9fafb; padding: 12px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; color: #374151; }
        .latest-insight .label { font-weight: 600; color: #6b7280; margin-right: 8px; }
        .dream-actions { display: flex; gap: 12px; }
        .btn-start { padding: 10px 20px; background: #10b981; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn-start:hover { background: #059669; }
        .btn-stop { padding: 10px 20px; background: #ef4444; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn-stop:hover { background: #dc2626; }
        .btn-run { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn-run:hover { background: #2563eb; }
        .btn-start:disabled, .btn-stop:disabled, .btn-run:disabled { background: #9ca3af; cursor: not-allowed; }
        .dream-run-result { background: #fff; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb; margin-bottom: 24px; }
        .dream-run-result h4 { font-size: 0.9rem; color: #374151; margin-bottom: 8px; }
        .run-stats { display: flex; gap: 20px; font-size: 0.85rem; color: #6b7280; flex-wrap: wrap; }
        .dream-insights h4 { font-size: 0.9rem; color: #374151; margin-bottom: 12px; }
        .insight-card { background: #fff; border-radius: 10px; padding: 16px; border: 1px solid #e5e7eb; margin-bottom: 12px; }
        .insight-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .insight-phase { font-size: 0.75rem; color: #fff; padding: 3px 10px; border-radius: 12px; font-weight: 600; text-transform: uppercase; }
        .insight-confidence { font-size: 0.75rem; color: #9ca3af; }
        .insight-content { font-size: 0.9rem; color: #374151; line-height: 1.5; }
        .insight-sources { font-size: 0.7rem; color: #9ca3af; margin-top: 8px; }
        .empty-state { color: #9ca3af; text-align: center; padding: 40px; font-size: 0.9rem; }
        .error-banner { background: #fef2f2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.9rem; }
      `}</style>
    </div>
  );
};