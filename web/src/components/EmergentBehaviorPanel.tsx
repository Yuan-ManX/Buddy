import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface EmergentBehaviorStats {
  total_observations: number;
  patterns_detected: number;
  promoted_patterns: number;
  suppressed_patterns: number;
  observation_rate: number;
}

interface Observation {
  id: string;
  agent_id: string;
  action: string;
  context: string;
  outcome: string;
  success: boolean;
  timestamp: string;
}

interface Pattern {
  id: string;
  name: string;
  description: string;
  type: 'BENEFICIAL' | 'NEUTRAL' | 'HARMFUL';
  status: string;
  frequency: number;
  confidence: number;
  agents_involved: string[];
  detected_at: string;
}

interface EmergenceReport {
  total_observations: number;
  total_patterns: number;
  promoted_patterns: number;
  suppressed_patterns: number;
  top_patterns: Pattern[];
  agent_contributions: Record<string, number>;
  emergence_timeline?: Array<{
    timestamp: string;
    event: string;
    pattern_id?: string;
  }>;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const EmergentBehaviorPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<EmergentBehaviorStats | null>(null);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [report, setReport] = useState<EmergenceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'observe' | 'patterns' | 'report'>('overview');

  // Observe form
  const [observeForm, setObserveForm] = useState({
    agent_id: '',
    action: '',
    context: '',
    outcome: '',
    success: false,
  });
  const [observing, setObserving] = useState(false);
  const [recordedObservation, setRecordedObservation] = useState<Observation | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, p, r] = await Promise.all([
        request<EmergentBehaviorStats>('/emergent-behavior/stats').catch(() => null),
        request<Pattern[]>('/emergent-behavior/patterns').catch(() => []),
        request<EmergenceReport>('/emergent-behavior/report').catch(() => null),
      ]);
      setStats(s);
      setPatterns(Array.isArray(p) ? p : (p as any)?.patterns || []);
      setReport(r);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load emergent behavior data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleObserve = async () => {
    if (!observeForm.agent_id.trim() || !observeForm.action.trim()) return;
    try {
      setObserving(true);
      const result = await request<Observation>('/emergent-behavior/observe', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: observeForm.agent_id,
          action: observeForm.action,
          context: observeForm.context,
          outcome: observeForm.outcome,
          success: observeForm.success,
        }),
      });
      setRecordedObservation(result);
      toast.success('Observation recorded successfully');
      setObserveForm({ agent_id: '', action: '', context: '', outcome: '', success: false });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setObserving(false);
    }
  };

  const handlePromote = async (patternId: string) => {
    try {
      await request(`/emergent-behavior/promote/${patternId}`, { method: 'POST' });
      toast.success('Pattern promoted successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleSuppress = async (patternId: string) => {
    try {
      await request(`/emergent-behavior/suppress/${patternId}`, { method: 'POST' });
      toast.success('Pattern suppressed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const typeColors: Record<string, string> = {
    BENEFICIAL: '#22c55e',
    NEUTRAL: '#f59e0b',
    HARMFUL: '#ef4444',
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    detected: '#3b82f6',
    promoted: '#8b5cf6',
    suppressed: '#ef4444',
    emerging: '#f59e0b',
    stable: '#22c55e',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Emergent Behavior Detector</h2>
          <p className="panel-subtitle">Detect and analyze emergent behaviors in multi-agent systems</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading emergent behavior data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Emergent Behavior Detector</h2>
        <p className="panel-subtitle">Detect, analyze, and manage emergent behaviors across agent interactions</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_observations}</span>
              <span className="stat-label">Total Observations</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.patterns_detected}</span>
              <span className="stat-label">Patterns Detected</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.promoted_patterns}</span>
              <span className="stat-label">Promoted</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#ef4444' }}>{stats.suppressed_patterns}</span>
              <span className="stat-label">Suppressed</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>
                {stats.observation_rate?.toFixed(1)}/s
              </span>
              <span className="stat-label">Observation Rate</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'observe', 'patterns', 'report'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Detector Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Observations</span>
                <strong>{stats.total_observations}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Patterns Detected</span>
                <strong style={{ color: '#22c55e' }}>{stats.patterns_detected}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Promoted Patterns</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.promoted_patterns}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Suppressed Patterns</span>
                <strong style={{ color: '#ef4444' }}>{stats.suppressed_patterns}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Observation Rate</span>
                <strong style={{ color: '#3b82f6' }}>{stats.observation_rate?.toFixed(1)}/s</strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Recent Patterns</h3>
              {patterns.length === 0 ? (
                <div className="panel-empty">No patterns detected yet</div>
              ) : (
                <div className="forge-skill-list">
                  {patterns.slice(0, 5).map(pattern => (
                    <div key={pattern.id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{pattern.name}</div>
                        <span className="dashboard-badge" style={{
                          background: typeColors[pattern.type] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {pattern.type}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{pattern.description}</div>
                        <div>Frequency: {pattern.frequency} | Confidence: {(pattern.confidence * 100).toFixed(1)}%</div>
                        <div>Agents: {pattern.agents_involved?.join(', ') || 'N/A'}</div>
                        <div>Detected: {new Date(pattern.detected_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Observe Section ── */}
      {activeSection === 'observe' && (
        <div className="dashboard-section">
          <h3>Record Observation</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={observeForm.agent_id}
                onChange={e => setObserveForm(f => ({ ...f, agent_id: e.target.value }))}
                placeholder="e.g. agent-001"
              />
            </div>
            <div className="form-group">
              <label>Action</label>
              <input
                type="text"
                value={observeForm.action}
                onChange={e => setObserveForm(f => ({ ...f, action: e.target.value }))}
                placeholder="e.g. coordinate, delegate, explore"
              />
            </div>
            <div className="form-group">
              <label>Context</label>
              <textarea
                rows={3}
                value={observeForm.context}
                onChange={e => setObserveForm(f => ({ ...f, context: e.target.value }))}
                placeholder="Describe the context of this observation"
              />
            </div>
            <div className="form-group">
              <label>Outcome</label>
              <textarea
                rows={3}
                value={observeForm.outcome}
                onChange={e => setObserveForm(f => ({ ...f, outcome: e.target.value }))}
                placeholder="Describe the outcome of this observation"
              />
            </div>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={observeForm.success}
                  onChange={e => setObserveForm(f => ({ ...f, success: e.target.checked }))}
                />
                Success
              </label>
            </div>
            <button
              className="btn-primary"
              onClick={handleObserve}
              disabled={observing || !observeForm.agent_id.trim() || !observeForm.action.trim()}
            >
              {observing ? 'Recording...' : 'Record Observation'}
            </button>
          </div>

          {recordedObservation && (
            <div className="dashboard-section" style={{ marginTop: 16 }}>
              <h3>Recorded Observation</h3>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">{recordedObservation.action}</div>
                  <span className="dashboard-badge" style={{
                    background: recordedObservation.success ? '#22c55e' : '#ef4444',
                    color: '#fff',
                  }}>
                    {recordedObservation.success ? 'Success' : 'Failure'}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div>Agent: {recordedObservation.agent_id}</div>
                  <div>Context: {recordedObservation.context}</div>
                  <div>Outcome: {recordedObservation.outcome}</div>
                  <div>ID: {recordedObservation.id}</div>
                  <div>Timestamp: {new Date(recordedObservation.timestamp).toLocaleString()}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Patterns Section ── */}
      {activeSection === 'patterns' && (
        <div className="dashboard-section">
          <h3>Detected Patterns ({patterns.length})</h3>
          {patterns.length === 0 ? (
            <div className="panel-empty">No patterns detected yet. Record observations to detect emergent patterns.</div>
          ) : (
            <div className="forge-skill-list">
              {patterns.map(pattern => (
                <div key={pattern.id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{pattern.name}</div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span className="dashboard-badge" style={{
                        background: typeColors[pattern.type] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {pattern.type}
                      </span>
                      <span className="dashboard-badge" style={{
                        background: statusColors[pattern.status] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {pattern.status}
                      </span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{pattern.description}</div>
                    <div>Frequency: {pattern.frequency} | Confidence: {(pattern.confidence * 100).toFixed(1)}%</div>
                    <div>Agents: {pattern.agents_involved?.join(', ') || 'N/A'}</div>
                    <div>Detected: {new Date(pattern.detected_at).toLocaleString()}</div>
                  </div>
                  <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                    <button
                      className="btn-primary"
                      onClick={() => handlePromote(pattern.id)}
                      style={{ background: '#22c55e', fontSize: '0.85rem', padding: '6px 14px' }}
                    >
                      Promote
                    </button>
                    <button
                      className="btn-primary"
                      onClick={() => handleSuppress(pattern.id)}
                      style={{ background: '#ef4444', fontSize: '0.85rem', padding: '6px 14px' }}
                    >
                      Suppress
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Report Section ── */}
      {activeSection === 'report' && (
        <div className="dashboard-section">
          {report ? (
            <>
              <h3>Emergence Report</h3>

              <h4 style={{ marginTop: 16 }}>Stats Overview</h4>
              <div className="dashboard-stat-row">
                <span>Total Observations</span>
                <strong>{report.total_observations}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Patterns</span>
                <strong style={{ color: '#22c55e' }}>{report.total_patterns}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Promoted Patterns</span>
                <strong style={{ color: '#8b5cf6' }}>{report.promoted_patterns}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Suppressed Patterns</span>
                <strong style={{ color: '#ef4444' }}>{report.suppressed_patterns}</strong>
              </div>

              <h4 style={{ marginTop: 24 }}>Top Patterns</h4>
              {report.top_patterns && report.top_patterns.length > 0 ? (
                <div className="forge-skill-list">
                  {report.top_patterns.map(pattern => (
                    <div key={pattern.id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{pattern.name}</div>
                        <span className="dashboard-badge" style={{
                          background: typeColors[pattern.type] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {pattern.type}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{pattern.description}</div>
                        <div>Frequency: {pattern.frequency} | Confidence: {(pattern.confidence * 100).toFixed(1)}%</div>
                        <div>Agents: {pattern.agents_involved?.join(', ') || 'N/A'}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No top patterns available</div>
              )}

              <h4 style={{ marginTop: 24 }}>Agent Contributions</h4>
              {report.agent_contributions && Object.keys(report.agent_contributions).length > 0 ? (
                <div className="forge-skill-list">
                  {Object.entries(report.agent_contributions).map(([agentId, count]) => (
                    <div key={agentId} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{agentId}</div>
                        <span className="dashboard-badge" style={{
                          background: '#3b82f6',
                          color: '#fff',
                        }}>
                          {count} contributions
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No agent contributions recorded</div>
              )}

              {report.emergence_timeline && report.emergence_timeline.length > 0 && (
                <>
                  <h4 style={{ marginTop: 24 }}>Emergence Timeline</h4>
                  <div className="forge-skill-list">
                    {report.emergence_timeline.map((entry, idx) => (
                      <div key={idx} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{entry.event}</div>
                          <span className="dashboard-badge" style={{
                            background: '#3b82f6',
                            color: '#fff',
                          }}>
                            {new Date(entry.timestamp).toLocaleString()}
                          </span>
                        </div>
                        {entry.pattern_id && (
                          <div className="forge-skill-meta">
                            <div>Pattern ID: {entry.pattern_id}</div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          ) : (
            <div className="panel-empty">No emergence report available yet. Record observations and detect patterns to generate a report.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default EmergentBehaviorPanel;