import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { SelfReflectionStats, SelfReflectionSession, SelfReflectionInsight, ReflectionResult, ActionRecord } from '../types';

export const SelfReflectionPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<SelfReflectionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'sessions' | 'reflect' | 'insights' | 'history'>('overview');

  // Session state
  const [sessionAgentId, setSessionAgentId] = useState('');
  const [activeSession, setActiveSession] = useState<SelfReflectionSession | null>(null);
  const [actionForm, setActionForm] = useState({ action_type: 'thought', description: '', context: '{}' });

  // Reflect state
  const [reflectSessionId, setReflectSessionId] = useState('');
  const [reflectResult, setReflectResult] = useState<ReflectionResult | null>(null);

  // Insights state
  const [insights, setInsights] = useState<SelfReflectionInsight[]>([]);
  const [insightFilter, setInsightFilter] = useState({ session_id: '', perspective: '', type: '' });

  // History state
  const [historyAgentId, setHistoryAgentId] = useState('');
  const [historySessions, setHistorySessions] = useState<SelfReflectionSession[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.selfReflection.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load self-reflection data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleStartSession = async () => {
    if (!sessionAgentId.trim()) return;
    try {
      const session = await api.selfReflection.startSession(sessionAgentId);
      setActiveSession(session);
      toast.success(`Session started: ${session.session_id}`);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordAction = async () => {
    if (!activeSession || !actionForm.description.trim()) return;
    try {
      let context: Record<string, unknown> | undefined;
      try { context = JSON.parse(actionForm.context); } catch {}

      await api.selfReflection.recordAction({
        session_id: activeSession.session_id,
        action_type: actionForm.action_type,
        description: actionForm.description,
        context,
      });
      toast.success('Action recorded');
      setActionForm({ action_type: 'thought', description: '', context: '{}' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleReflect = async () => {
    if (!reflectSessionId.trim()) return;
    try {
      const result = await api.selfReflection.reflect(reflectSessionId);
      setReflectResult(result);
      toast.success(`Reflection complete: ${result.total_insights} insights`);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadInsights = async () => {
    try {
      const params: any = {};
      if (insightFilter.session_id) params.session_id = insightFilter.session_id;
      if (insightFilter.perspective) params.perspective = insightFilter.perspective;
      const result = await api.selfReflection.insights(params);
      setInsights(result.insights);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLoadHistory = async () => {
    if (!historyAgentId.trim()) return;
    try {
      const result = await api.selfReflection.history(historyAgentId);
      setHistorySessions(result.sessions);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyInsight = async (insightId: string) => {
    try {
      await api.selfReflection.applyInsight(insightId);
      toast.success('Insight applied');
      handleLoadInsights();
    } catch (e: any) { toast.error(e.message); }
  };

  const perspectiveColors: Record<string, string> = {
    self: '#4f6ef7',
    user: '#22c55e',
    system: '#f59e0b',
    peer: '#8b5cf6',
    external: '#ef4444',
  };

  const priorityColors: Record<string, string> = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#22c55e',
  };

  const typeColors: Record<string, string> = {
    improvement: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
    observation: '#3b82f6',
    pattern: '#8b5cf6',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Self-Reflection</h2>
          <p className="panel-subtitle">Agent introspection and continuous improvement</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading self-reflection data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Self-Reflection</h2>
        <p className="panel-subtitle">Agent introspection, pattern recognition, and continuous improvement loop</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_sessions}</span><span className="stat-label">Total Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.active_sessions}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_actions}</span><span className="stat-label">Actions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_insights}</span><span className="stat-label">Insights</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{(stats.average_confidence * 100).toFixed(0)}%</span><span className="stat-label">Avg Confidence</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'sessions', 'reflect', 'insights', 'history'] as const).map(s => (
          <button key={s} className={`forge-tab ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Reflection Summary</h3>
          <div className="dashboard-stat-row"><span>Total Sessions</span><strong>{stats.total_sessions}</strong></div>
          <div className="dashboard-stat-row"><span>Active Sessions</span><strong>{stats.active_sessions}</strong></div>
          <div className="dashboard-stat-row"><span>Total Actions Recorded</span><strong>{stats.total_actions}</strong></div>
          <div className="dashboard-stat-row"><span>Total Insights Generated</span><strong>{stats.total_insights}</strong></div>
          <div className="dashboard-stat-row"><span>Average Confidence</span><strong>{(stats.average_confidence * 100).toFixed(0)}%</strong></div>

          <h3 style={{ marginTop: 20 }}>Insights by Perspective</h3>
          {Object.entries(stats.by_perspective).length > 0 ? (
            Object.entries(stats.by_perspective).map(([perspective, count]) => (
              <div key={perspective} className="dashboard-stat-row">
                <span style={{ color: perspectiveColors[perspective] || '#666', fontWeight: 600, textTransform: 'capitalize' }}>
                  {perspective}
                </span>
                <strong>{count}</strong>
              </div>
            ))
          ) : (
            <div className="panel-empty">No perspective data yet</div>
          )}
        </div>
      )}

      {/* Sessions */}
      {activeSection === 'sessions' && (
        <div className="dashboard-section">
          <h3>Manage Reflection Sessions</h3>

          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <h3>Start New Session</h3>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={sessionAgentId}
                onChange={e => setSessionAgentId(e.target.value)}
                placeholder="Enter agent ID"
              />
            </div>
            <button className="btn-primary" onClick={handleStartSession}>Start Session</button>
          </div>

          {activeSession && (
            <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
              <h3>Active Session: {activeSession.session_id}</h3>
              <div className="forge-skill-meta" style={{ marginBottom: 12 }}>
                <div>Agent: {activeSession.agent_id} | Status: {activeSession.status}</div>
                <div>Actions: {activeSession.action_count} | Insights: {activeSession.insight_count}</div>
                <div>Created: {new Date(activeSession.created_at).toLocaleString()}</div>
              </div>

              <h4>Record Action</h4>
              <div className="form-row">
                <div className="form-group">
                  <label>Action Type</label>
                  <select value={actionForm.action_type} onChange={e => setActionForm(f => ({ ...f, action_type: e.target.value }))}>
                    {['thought', 'decision', 'tool_call', 'response', 'error', 'correction'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group" style={{ flex: 2 }}>
                  <label>Description</label>
                  <input
                    type="text"
                    value={actionForm.description}
                    onChange={e => setActionForm(f => ({ ...f, description: e.target.value }))}
                    placeholder="What happened?"
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Context (JSON)</label>
                <textarea
                  rows={3}
                  value={actionForm.context}
                  onChange={e => setActionForm(f => ({ ...f, context: e.target.value }))}
                  placeholder='{"key": "value"}'
                  style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
                />
              </div>
              <button className="btn-primary" onClick={handleRecordAction}>Record Action</button>
            </div>
          )}
        </div>
      )}

      {/* Reflect */}
      {activeSection === 'reflect' && (
        <div className="dashboard-section">
          <h3>Trigger Reflection</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session ID</label>
              <input
                type="text"
                value={reflectSessionId}
                onChange={e => setReflectSessionId(e.target.value)}
                placeholder="Enter session ID to reflect on"
              />
            </div>
            <button className="btn-primary" onClick={handleReflect}>Run Reflection</button>
          </div>

          {reflectResult && (
            <div style={{ marginTop: 16 }}>
              <div className="stats-bar" style={{ marginBottom: 16 }}>
                <div className="stat-item"><div className="stat-content"><span className="stat-value">{reflectResult.total_insights}</span><span className="stat-label">Insights</span></div></div>
                <div className="stat-item"><div className="stat-content"><span className="stat-value">{(reflectResult.average_confidence * 100).toFixed(0)}%</span><span className="stat-label">Avg Confidence</span></div></div>
              </div>

              <h4>Generated Insights</h4>
              <div className="forge-skill-list">
                {reflectResult.insights.map((insight: SelfReflectionInsight) => (
                  <div key={insight.insight_id} className="forge-skill-card">
                    <div className="forge-skill-header">
                      <div className="forge-skill-name">{insight.description}</div>
                      <span className="dashboard-badge" style={{ background: typeColors[insight.type] || '#666', color: '#fff' }}>
                        {insight.type}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      <div>
                        <span style={{ color: perspectiveColors[insight.perspective] || '#666', fontWeight: 600 }}>
                          {insight.perspective}
                        </span>
                        {' | '}
                        <span style={{ color: priorityColors[insight.priority] || '#666', fontWeight: 600 }}>
                          {insight.priority.toUpperCase()}
                        </span>
                        {' | Confidence: '}{(insight.confidence * 100).toFixed(0)}%
                      </div>
                      <div style={{ marginTop: 4 }}>
                        {insight.actionable && (
                          <span className="dashboard-badge active" style={{ marginRight: 4 }}>Actionable</span>
                        )}
                        {insight.applied && (
                          <span className="dashboard-badge active" style={{ background: '#22c55e', color: '#fff' }}>Applied</span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 4 }}>
                        {new Date(insight.created_at).toLocaleString()}
                      </div>
                    </div>
                    {!insight.applied && insight.actionable && (
                      <div style={{ marginTop: 8 }}>
                        <button className="btn-sm" style={{ background: '#4f6ef7', color: '#fff', border: 'none' }} onClick={() => handleApplyInsight(insight.insight_id)}>
                          Apply Insight
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Insights */}
      {activeSection === 'insights' && (
        <div className="dashboard-section">
          <h3>Browse Insights</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID</label>
                <input type="text" value={insightFilter.session_id} onChange={e => setInsightFilter(f => ({ ...f, session_id: e.target.value }))} placeholder="Filter by session" />
              </div>
              <div className="form-group">
                <label>Perspective</label>
                <select value={insightFilter.perspective} onChange={e => setInsightFilter(f => ({ ...f, perspective: e.target.value }))}>
                  <option value="">All</option>
                  {['self', 'user', 'system', 'peer', 'external'].map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={insightFilter.type} onChange={e => setInsightFilter(f => ({ ...f, type: e.target.value }))}>
                  <option value="">All</option>
                  {['improvement', 'warning', 'error', 'observation', 'pattern'].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <button className="btn-primary" onClick={handleLoadInsights}>Load Insights</button>
          </div>

          {insights.length === 0 ? (
            <div className="panel-empty">No insights loaded. Use the filters above to load insights.</div>
          ) : (
            <div className="forge-skill-list">
              {insights.map((insight: SelfReflectionInsight) => (
                <div key={insight.insight_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{insight.description}</div>
                    <span className="dashboard-badge" style={{ background: typeColors[insight.type] || '#666', color: '#fff' }}>
                      {insight.type}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      <span style={{ color: perspectiveColors[insight.perspective] || '#666', fontWeight: 600 }}>
                        {insight.perspective}
                      </span>
                      {' | '}
                      <span style={{ color: priorityColors[insight.priority] || '#666', fontWeight: 600 }}>
                        {insight.priority.toUpperCase()}
                      </span>
                      {' | Confidence: '}{(insight.confidence * 100).toFixed(0)}%
                    </div>
                    <div>Session: {insight.session_id}</div>
                    <div style={{ marginTop: 4 }}>
                      {insight.actionable && (
                        <span className="dashboard-badge active" style={{ marginRight: 4 }}>Actionable</span>
                      )}
                      {insight.applied && (
                        <span className="dashboard-badge active" style={{ background: '#22c55e', color: '#fff' }}>Applied</span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 4 }}>
                      {new Date(insight.created_at).toLocaleString()}
                    </div>
                  </div>
                  {!insight.applied && insight.actionable && (
                    <div style={{ marginTop: 8 }}>
                      <button className="btn-sm" style={{ background: '#4f6ef7', color: '#fff', border: 'none' }} onClick={() => handleApplyInsight(insight.insight_id)}>
                        Apply Insight
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* History */}
      {activeSection === 'history' && (
        <div className="dashboard-section">
          <h3>Agent History</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label>Agent ID</label>
                <input
                  type="text"
                  value={historyAgentId}
                  onChange={e => setHistoryAgentId(e.target.value)}
                  placeholder="Enter agent ID"
                />
              </div>
              <div className="form-group" style={{ alignSelf: 'flex-end' }}>
                <button className="btn-primary" onClick={handleLoadHistory}>Load History</button>
              </div>
            </div>
          </div>

          {historySessions.length === 0 ? (
            <div className="panel-empty">Enter an agent ID and click "Load History" to view sessions.</div>
          ) : (
            <div className="forge-skill-list">
              {historySessions.map((session: SelfReflectionSession) => (
                <div key={session.session_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{session.session_id}</div>
                    <span className="dashboard-badge" style={{
                      background: session.status === 'active' ? '#22c55e' : '#9ca3af',
                      color: '#fff',
                    }}>
                      {session.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Agent: {session.agent_id}</div>
                    <div>Actions: {session.action_count} | Insights: {session.insight_count}</div>
                    <div>Created: {new Date(session.created_at).toLocaleString()}</div>
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

export default SelfReflectionPanel;