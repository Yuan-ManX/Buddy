import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface ExperienceStats {
  total_experiences: number;
  replay_buffer: { total: number; priority_weighted: Record<string, number> };
  compression: {
    total_compressed: number;
    total_sessions: number;
    avg_compression_ratio: number;
    bytes_saved: number;
  };
  evolution: {
    total_evolutions: number;
    agents_evolved: number;
    total_improvements: number;
  };
  analytics: {
    total_reports: number;
    by_outcome: Record<string, number>;
    by_type: Record<string, number>;
    avg_tokens: number;
    avg_latency_ms: number;
    total_cost: number;
  };
}

export const ExperiencePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<ExperienceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'record' | 'replay' | 'compress' | 'evolve' | 'analytics'>('overview');

  // Record form
  const [recordForm, setRecordForm] = useState({
    experience_type: 'conversation',
    agent_id: '',
    session_id: '',
    description: '',
    outcome: 'success',
    tokens_used: '0',
    latency_ms: '0',
    cost: '0',
  });

  // Replay form
  const [replayBatchSize, setReplayBatchSize] = useState('10');
  const [replayResult, setReplayResult] = useState<any[]>([]);

  // Compress form
  const [compressSessionId, setCompressSessionId] = useState('');
  const [compressResult, setCompressResult] = useState<any>(null);

  // Evolve form
  const [evolveAgentId, setEvolveAgentId] = useState('');
  const [evolveResult, setEvolveResult] = useState<any>(null);

  // Analytics
  const [analyticsAgentId, setAnalyticsAgentId] = useState('');
  const [analyticsResult, setAnalyticsResult] = useState<any>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/experience/stats');
      const data = await res.json();
      setStats(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load experience stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleRecord = async () => {
    try {
      const res = await fetch('/api/experience/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          experience_type: recordForm.experience_type,
          agent_id: recordForm.agent_id,
          session_id: recordForm.session_id,
          description: recordForm.description,
          outcome: recordForm.outcome,
          tokens_used: parseInt(recordForm.tokens_used) || 0,
          latency_ms: parseInt(recordForm.latency_ms) || 0,
          cost: parseFloat(recordForm.cost) || 0,
        }),
      });
      const data = await res.json();
      toast?.success?.('Experience recorded: ' + data.experience_id);
      setRecordForm({ experience_type: 'conversation', agent_id: '', session_id: '', description: '', outcome: 'success', tokens_used: '0', latency_ms: '0', cost: '0' });
      loadStats();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleSample = async () => {
    try {
      const res = await fetch('/api/experience/replay/sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_size: parseInt(replayBatchSize) || 10 }),
      });
      const data = await res.json();
      setReplayResult(data.experiences);
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleCompress = async () => {
    try {
      const res = await fetch('/api/experience/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: compressSessionId }),
      });
      const data = await res.json();
      setCompressResult(data);
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleEvolve = async () => {
    try {
      const res = await fetch('/api/experience/evolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: evolveAgentId }),
      });
      const data = await res.json();
      setEvolveResult(data);
      loadStats();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleAnalytics = async () => {
    try {
      const qs = analyticsAgentId ? `?agent_id=${analyticsAgentId}` : '';
      const res = await fetch(`/api/experience/analytics${qs}`);
      const data = await res.json();
      setAnalyticsResult(data);
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  if (loading) return <div className="panel loading">Loading experience engine...</div>;

  return (
    <div className="panel experience-panel">
      <div className="panel-header">
        <h2>Experience Engine</h2>
        <span className="panel-badge">
          {stats ? `${stats.total_experiences} experiences` : 'Initializing'}
        </span>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-tabs">
        {(['overview', 'record', 'replay', 'compress', 'evolve', 'analytics'] as const).map((s) => (
          <button
            key={s}
            className={`panel-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="panel-content">
        {activeSection === 'overview' && stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_experiences}</div>
              <div className="stat-label">Total Experiences</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.replay_buffer?.total || 0}</div>
              <div className="stat-label">Replay Buffer</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.compression?.total_compressed || 0}</div>
              <div className="stat-label">Compressed Sessions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.evolution?.total_evolutions || 0}</div>
              <div className="stat-label">Evolutions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.analytics?.total_reports || 0}</div>
              <div className="stat-label">Reports</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">${(stats.analytics?.total_cost || 0).toFixed(4)}</div>
              <div className="stat-label">Total Cost</div>
            </div>

            {stats.analytics?.by_outcome && (
              <div className="section-card full-width">
                <h3>Outcome Distribution</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.analytics.by_outcome).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.analytics.by_outcome).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.analytics?.by_type && (
              <div className="section-card full-width">
                <h3>Experience Types</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.analytics.by_type).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.analytics.by_type).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'record' && (
          <div className="form-section">
            <h3>Record New Experience</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Type</label>
                <select value={recordForm.experience_type} onChange={e => setRecordForm({ ...recordForm, experience_type: e.target.value })}>
                  <option value="conversation">Conversation</option>
                  <option value="task_execution">Task Execution</option>
                  <option value="tool_call">Tool Call</option>
                  <option value="reasoning">Reasoning</option>
                  <option value="learning">Learning</option>
                </select>
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input type="text" value={recordForm.agent_id} onChange={e => setRecordForm({ ...recordForm, agent_id: e.target.value })} placeholder="agent-..." />
              </div>
              <div className="form-group">
                <label>Session ID</label>
                <input type="text" value={recordForm.session_id} onChange={e => setRecordForm({ ...recordForm, session_id: e.target.value })} placeholder="session-..." />
              </div>
              <div className="form-group">
                <label>Outcome</label>
                <select value={recordForm.outcome} onChange={e => setRecordForm({ ...recordForm, outcome: e.target.value })}>
                  <option value="success">Success</option>
                  <option value="partial">Partial</option>
                  <option value="failure">Failure</option>
                </select>
              </div>
              <div className="form-group full-width">
                <label>Description</label>
                <textarea value={recordForm.description} onChange={e => setRecordForm({ ...recordForm, description: e.target.value })} placeholder="What happened..." rows={3} />
              </div>
              <div className="form-group">
                <label>Tokens Used</label>
                <input type="number" value={recordForm.tokens_used} onChange={e => setRecordForm({ ...recordForm, tokens_used: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Latency (ms)</label>
                <input type="number" value={recordForm.latency_ms} onChange={e => setRecordForm({ ...recordForm, latency_ms: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Cost ($)</label>
                <input type="number" step="0.0001" value={recordForm.cost} onChange={e => setRecordForm({ ...recordForm, cost: e.target.value })} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleRecord}>Record Experience</button>
          </div>
        )}

        {activeSection === 'replay' && (
          <div className="form-section">
            <h3>Replay Buffer Sampling</h3>
            <div className="form-group">
              <label>Batch Size</label>
              <input type="number" value={replayBatchSize} onChange={e => setReplayBatchSize(e.target.value)} min="1" max="100" />
            </div>
            <button className="btn-primary" onClick={handleSample}>Sample Experiences</button>
            {replayResult.length > 0 && (
              <div className="result-list">
                <h4>Results ({replayResult.length})</h4>
                {replayResult.map((exp: any, i: number) => (
                  <div key={i} className="result-item">
                    <span className="result-type">{exp.experience_type}</span>
                    <span className="result-desc">{exp.description}</span>
                    <span className={`result-badge ${exp.outcome}`}>{exp.outcome}</span>
                    <span className="result-priority">P: {exp.priority?.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSection === 'compress' && (
          <div className="form-section">
            <h3>Compress Session Trajectory</h3>
            <div className="form-group">
              <label>Session ID</label>
              <input type="text" value={compressSessionId} onChange={e => setCompressSessionId(e.target.value)} placeholder="session-..." />
            </div>
            <button className="btn-primary" onClick={handleCompress}>Compress</button>
            {compressResult && (
              <div className="result-card">
                <pre>{JSON.stringify(compressResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeSection === 'evolve' && (
          <div className="form-section">
            <h3>Evolve Agent from Experience</h3>
            <div className="form-group">
              <label>Agent ID</label>
              <input type="text" value={evolveAgentId} onChange={e => setEvolveAgentId(e.target.value)} placeholder="agent-..." />
            </div>
            <button className="btn-primary" onClick={handleEvolve}>Evolve</button>
            {evolveResult && (
              <div className="result-card">
                <pre>{JSON.stringify(evolveResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeSection === 'analytics' && (
          <div className="form-section">
            <h3>Experience Analytics</h3>
            <div className="form-group">
              <label>Agent ID (optional)</label>
              <input type="text" value={analyticsAgentId} onChange={e => setAnalyticsAgentId(e.target.value)} placeholder="Leave empty for all agents" />
            </div>
            <button className="btn-primary" onClick={handleAnalytics}>Generate Report</button>
            {analyticsResult && (
              <div className="result-card">
                <pre>{JSON.stringify(analyticsResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};