import React, { useState, useEffect, useCallback } from 'react';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

interface CollaborationStats {
  total_sessions: number;
  active_sessions: number;
  registered_agents: number;
  session_history_count: number;
  agents_by_role: Record<string, number>;
  recent_sessions: Array<{
    session_id: string;
    mode: string;
    topic: string;
    collaborators: number;
    contributions: number;
    consensus_achieved: boolean;
  }>;
}

interface DebateResult {
  session_id: string;
  consensus: { decision: string; confidence: number; achieved: boolean } | null;
  contributions: number;
  final_output: string;
}

interface RoundtableResult {
  session_id: string;
  collaborators: Array<{ agent_id: string; name: string; role: string }>;
  contributions: number;
  final_output: string;
}

export const CollaborativeIntelligencePanel: React.FC = () => {
  const [stats, setStats] = useState<CollaborationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'debate' | 'roundtable' | 'history'>('overview');

  // Debate form
  const [debateTopic, setDebateTopic] = useState('');
  const [debateAgentIds, setDebateAgentIds] = useState('');
  const [debateRounds, setDebateRounds] = useState(3);
  const [debateResult, setDebateResult] = useState<DebateResult | null>(null);
  const [debateLoading, setDebateLoading] = useState(false);

  // Roundtable form
  const [roundtableTopic, setRoundtableTopic] = useState('');
  const [roundtableAgentIds, setRoundtableAgentIds] = useState('');
  const [roundtableResult, setRoundtableResult] = useState<RoundtableResult | null>(null);
  const [roundtableLoading, setRoundtableLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const statsRes = await request<CollaborationStats>('/collaboration/stats');
      setStats(statsRes);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunDebate = async () => {
    if (!debateTopic.trim() || !debateAgentIds.trim()) return;
    try {
      setDebateLoading(true);
      const agentIds = debateAgentIds.split(',').map((s) => s.trim()).filter(Boolean);
      const result = await request<DebateResult>('/collaboration/debate', {
        method: 'POST',
        body: JSON.stringify({ topic: debateTopic, agent_ids: agentIds, max_rounds: debateRounds }),
      });
      setDebateResult(result);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Debate failed');
    } finally {
      setDebateLoading(false);
    }
  };

  const handleRunRoundtable = async () => {
    if (!roundtableTopic.trim() || !roundtableAgentIds.trim()) return;
    try {
      setRoundtableLoading(true);
      const agentIds = roundtableAgentIds.split(',').map((s) => s.trim()).filter(Boolean);
      const result = await request<RoundtableResult>('/collaboration/roundtable', {
        method: 'POST',
        body: JSON.stringify({ topic: roundtableTopic, agent_ids: agentIds }),
      });
      setRoundtableResult(result);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Roundtable failed');
    } finally {
      setRoundtableLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header"><h2>Collaborative Intelligence</h2></div>
        <div className="panel-body" style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
          <div className="loading-spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Collaborative Intelligence</h2>
        <span className="panel-badge" style={{ background: stats ? '#22c55e' : '#ef4444' }}>
          {stats ? 'Active' : 'Offline'}
        </span>
      </div>

      {error && (
        <div className="error-banner" style={{ background: '#fef2f2', color: '#dc2626', padding: '12px', margin: '0 16px', borderRadius: '8px' }}>
          {error}
        </div>
      )}

      <div className="tab-bar" style={{ display: 'flex', gap: '8px', padding: '16px', borderBottom: '1px solid #e5e7eb', flexWrap: 'wrap' }}>
        {(['overview', 'debate', 'roundtable', 'history'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px', border: 'none', borderRadius: '6px', cursor: 'pointer',
              background: activeTab === tab ? '#3b82f6' : '#f3f4f6',
              color: activeTab === tab ? '#fff' : '#374151',
              fontSize: '13px', fontWeight: 500,
            }}
          >
            {tab === 'overview' ? 'Overview' : tab === 'debate' ? 'Debate' : tab === 'roundtable' ? 'Roundtable' : 'History'}
          </button>
        ))}
      </div>

      <div className="panel-body" style={{ padding: '16px' }}>
        {activeTab === 'overview' && stats && (
          <div>
            {/* Collaboration Stats */}
            <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
              <div style={statCardStyle}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#3b82f6' }}>{stats.total_sessions}</div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>Total Sessions</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#8b5cf6' }}>{stats.active_sessions}</div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>Active Sessions</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#22c55e' }}>{stats.registered_agents}</div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>Registered Agents</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#f59e0b' }}>{stats.session_history_count}</div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>History Count</div>
              </div>
            </div>

            {/* Agent Roles Distribution */}
            {Object.keys(stats.agents_by_role).length > 0 && (
              <div className="section" style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>Agent Roles</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {Object.entries(stats.agents_by_role).map(([role, count]) => (
                    <div key={role} style={{
                      padding: '8px 14px', background: '#f9fafb', borderRadius: '20px',
                      border: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: '8px',
                    }}>
                      <span style={{ fontSize: '13px', fontWeight: 500, textTransform: 'capitalize' }}>{role}</span>
                      <span style={{
                        padding: '2px 8px', borderRadius: '10px', fontSize: '12px', fontWeight: 600,
                        background: '#3b82f6', color: '#fff',
                      }}>{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Collaboration Modes */}
            <div className="section" style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>Collaboration Modes</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                {['debate', 'roundtable', 'delegation', 'voting', 'synthesis', 'peer_review'].map((mode) => (
                  <div key={mode} style={{
                    padding: '12px', background: '#f9fafb', borderRadius: '8px',
                    border: '1px solid #e5e7eb', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: '18px', marginBottom: '4px' }}>
                      {mode === 'debate' ? '🗣️' : mode === 'roundtable' ? '🔄' : mode === 'delegation' ? '📤' : mode === 'voting' ? '🗳️' : mode === 'synthesis' ? '🧬' : '🔍'}
                    </div>
                    <div style={{ fontSize: '12px', fontWeight: 500, textTransform: 'capitalize' }}>
                      {mode.replace(/_/g, ' ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'debate' && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#374151' }}>
                Debate Topic
              </label>
              <textarea
                value={debateTopic}
                onChange={(e) => setDebateTopic(e.target.value)}
                placeholder="Enter the topic for multi-agent debate..."
                rows={3}
                style={textareaStyle}
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#374151' }}>
                Agent IDs (comma-separated, minimum 2)
              </label>
              <input
                value={debateAgentIds}
                onChange={(e) => setDebateAgentIds(e.target.value)}
                placeholder="agent-strategy-001, agent-research-001"
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#374151' }}>
                Max Rounds: {debateRounds}
              </label>
              <input type="range" min="1" max="10" value={debateRounds}
                onChange={(e) => setDebateRounds(parseInt(e.target.value))}
                style={{ width: '100%' }} />
            </div>
            <button onClick={handleRunDebate} disabled={debateLoading || !debateTopic.trim() || !debateAgentIds.trim()} style={{
              width: '100%', padding: '12px', background: '#3b82f6', color: '#fff',
              border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
            }}>
              {debateLoading ? 'Running Debate...' : 'Run Multi-Agent Debate'}
            </button>

            {debateResult && (
              <div style={{ marginTop: '16px' }}>
                {debateResult.consensus && (
                  <div style={{
                    padding: '12px', borderRadius: '8px', marginBottom: '12px',
                    background: debateResult.consensus.achieved ? '#f0fdf4' : '#fef2f2',
                    border: `1px solid ${debateResult.consensus.achieved ? '#bbf7d0' : '#fecaca'}`,
                  }}>
                    <div style={{ fontWeight: 600, fontSize: '14px', color: debateResult.consensus.achieved ? '#166534' : '#991b1b' }}>
                      Consensus: {debateResult.consensus.decision}
                    </div>
                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                      Confidence: {(debateResult.consensus.confidence * 100).toFixed(0)}% | Achieved: {debateResult.consensus.achieved ? 'Yes' : 'No'}
                    </div>
                  </div>
                )}
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
                  Session: {debateResult.session_id} | {debateResult.contributions} contributions
                </div>
                {debateResult.final_output && (
                  <div style={{ padding: '12px', background: '#f9fafb', borderRadius: '8px', fontSize: '13px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                    {debateResult.final_output}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'roundtable' && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#374151' }}>
                Roundtable Topic
              </label>
              <textarea
                value={roundtableTopic}
                onChange={(e) => setRoundtableTopic(e.target.value)}
                placeholder="Enter the topic for roundtable discussion..."
                rows={3}
                style={textareaStyle}
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: '#374151' }}>
                Agent IDs (comma-separated)
              </label>
              <input
                value={roundtableAgentIds}
                onChange={(e) => setRoundtableAgentIds(e.target.value)}
                placeholder="agent-strategy-001, agent-engineering-001, agent-research-001"
                style={inputStyle}
              />
            </div>
            <button onClick={handleRunRoundtable} disabled={roundtableLoading || !roundtableTopic.trim() || !roundtableAgentIds.trim()} style={{
              width: '100%', padding: '12px', background: '#8b5cf6', color: '#fff',
              border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
            }}>
              {roundtableLoading ? 'Running Roundtable...' : 'Run Multi-Agent Roundtable'}
            </button>

            {roundtableResult && (
              <div style={{ marginTop: '16px' }}>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
                    Session: {roundtableResult.session_id} | {roundtableResult.contributions} contributions
                  </div>
                  {roundtableResult.collaborators.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
                      {roundtableResult.collaborators.map((c, i) => (
                        <div key={i} style={{
                          padding: '6px 12px', background: '#f9fafb', borderRadius: '16px',
                          border: '1px solid #e5e7eb', fontSize: '12px',
                        }}>
                          <span style={{ fontWeight: 600 }}>{c.name || c.agent_id}</span>
                          <span style={{ color: '#6b7280', marginLeft: '6px' }}>({c.role})</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {roundtableResult.final_output && (
                  <div style={{ padding: '12px', background: '#f9fafb', borderRadius: '8px', fontSize: '13px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                    {roundtableResult.final_output}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && stats && (
          <div>
            {stats.recent_sessions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
                No collaboration sessions yet. Run a debate or roundtable to get started.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {stats.recent_sessions.map((session) => (
                  <div key={session.session_id} style={{
                    padding: '12px', background: '#f9fafb', borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                        background: session.mode === 'debate' ? '#fef3c7' : '#dbeafe',
                        color: session.mode === 'debate' ? '#92400e' : '#1e40af',
                        textTransform: 'capitalize',
                      }}>
                        {session.mode}
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: 500, color: '#374151', flex: 1 }}>
                        {session.topic.length > 60 ? session.topic.slice(0, 60) + '...' : session.topic}
                      </span>
                      <span style={{
                        padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
                        background: session.consensus_achieved ? '#bbf7d0' : '#fecaca',
                        color: session.consensus_achieved ? '#166534' : '#991b1b',
                      }}>
                        {session.consensus_achieved ? 'Consensus' : 'No Consensus'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#6b7280' }}>
                      <span>{session.collaborators} collaborators</span>
                      <span>{session.contributions} contributions</span>
                      <span style={{ fontFamily: 'monospace', fontSize: '10px' }}>{session.session_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const statCardStyle: React.CSSProperties = {
  padding: '16px', background: '#f9fafb', borderRadius: '10px',
  border: '1px solid #e5e7eb', textAlign: 'center',
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', border: '1px solid #d1d5db',
  borderRadius: '8px', fontSize: '13px', fontFamily: 'inherit', boxSizing: 'border-box',
};

const textareaStyle: React.CSSProperties = {
  width: '100%', padding: '12px', border: '1px solid #d1d5db',
  borderRadius: '8px', fontSize: '13px', resize: 'vertical', fontFamily: 'inherit',
  boxSizing: 'border-box',
};