import React, { useState, useEffect, useCallback } from 'react';

interface RuntimeMetrics {
  total_sessions: number;
  successful_sessions: number;
  failed_sessions: number;
  success_rate: number;
  avg_session_time_ms: number;
  phase_distribution: Record<string, number>;
  total_events_published: number;
  total_knowledge_shared: number;
  active_sessions: number;
  active_agents: number;
}

interface RuntimeSession {
  session_id: string;
  agent_id: string;
  mode: string;
  status: string;
  phases: string[];
  phase_results: Record<string, any>;
  phase_timings: Record<string, number>;
  errors: string[];
  warnings: string[];
}

interface ActivityEntry {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  agent_id: string;
}

export const UnifiedConsole: React.FC = () => {
  const [metrics, setMetrics] = useState<RuntimeMetrics | null>(null);
  const [sessions, setSessions] = useState<RuntimeSession[]>([]);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [showExecute, setShowExecute] = useState(false);
  const [execForm, setExecForm] = useState({
    agent_id: 'buddy-coder',
    query: '',
    mode: 'full',
  });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'sessions' | 'activity' | 'subsystems'>('overview');

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch('/api/unified-runtime/metrics');
      setMetrics(await res.json());
    } catch (e) { console.error('Fetch metrics failed:', e); }
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch('/api/unified-runtime/sessions');
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (e) { console.error('Fetch sessions failed:', e); }
  }, []);

  const fetchActivity = useCallback(async () => {
    try {
      const res = await fetch('/api/unified-runtime/activity');
      const data = await res.json();
      setActivity(data.entries || []);
    } catch (e) { console.error('Fetch activity failed:', e); }
  }, []);

  useEffect(() => {
    fetchMetrics();
    fetchSessions();
    fetchActivity();
    const interval = setInterval(() => {
      fetchMetrics();
      fetchActivity();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchMetrics, fetchActivity]);

  const executeTask = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/unified-runtime/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(execForm),
      });
      const data = await res.json();
      setShowExecute(false);
      fetchMetrics();
      fetchSessions();
      fetchActivity();
    } catch (e) { console.error('Execute failed:', e); }
    setLoading(false);
  };

  const subsystemStatus = [
    { name: 'Reasoning Engine', key: 'reasoning', endpoint: '/api/reasoning/stats' },
    { name: 'Tool Composer', key: 'tool_composer', endpoint: '/api/tool-composer/stats' },
    { name: 'Context Manager', key: 'context_manager', endpoint: '/api/context-manager/stats' },
    { name: 'Model Proxy', key: 'model_proxy', endpoint: '/api/model-proxy/stats' },
    { name: 'Skill Compiler', key: 'skill_compiler', endpoint: '/api/skill-compiler/stats' },
    { name: 'Reflection Engine', key: 'reflection', endpoint: '/api/reflection/stats' },
    { name: 'Intent Engine', key: 'intent', endpoint: '/api/intent/stats' },
    { name: 'Fleet Manager', key: 'fleet', endpoint: '/api/fleet/stats' },
    { name: 'Event Pipeline', key: 'event_pipeline', endpoint: '/api/event-pipeline/stats' },
    { name: 'Knowledge Network', key: 'knowledge_network', endpoint: '/api/knowledge-network/stats' },
  ];

  const [subsystemChecks, setSubsystemChecks] = useState<Record<string, string>>({});

  useEffect(() => {
    subsystemStatus.forEach(async (sub) => {
      try {
        const res = await fetch(sub.endpoint);
        if (res.ok) {
          setSubsystemChecks(prev => ({ ...prev, [sub.key]: 'online' }));
        } else {
          setSubsystemChecks(prev => ({ ...prev, [sub.key]: 'error' }));
        }
      } catch {
        setSubsystemChecks(prev => ({ ...prev, [sub.key]: 'offline' }));
      }
    });
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Unified Console</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Central monitoring and control for all Buddy agent subsystems</p>
        </div>
        <button
          onClick={() => setShowExecute(true)}
          style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
        >
          + Execute Task
        </button>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #e5e7eb', paddingBottom: 0 }}>
        {(['overview', 'sessions', 'activity', 'subsystems'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: 'none',
              borderBottom: activeTab === tab ? '2px solid #2563eb' : '2px solid transparent',
              color: activeTab === tab ? '#2563eb' : '#6b7280',
              fontWeight: activeTab === tab ? 600 : 400,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {tab === 'overview' ? 'Overview' : tab === 'sessions' ? 'Sessions' : tab === 'activity' ? 'Activity' : 'Subsystems'}
          </button>
        ))}
      </div>

      {/* Execute Task Modal */}
      {showExecute && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 16, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Execute Task</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input
              value={execForm.agent_id}
              onChange={e => setExecForm({ ...execForm, agent_id: e.target.value })}
              placeholder="Agent ID"
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            />
            <textarea
              value={execForm.query}
              onChange={e => setExecForm({ ...execForm, query: e.target.value })}
              placeholder="Task description..."
              rows={3}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13, resize: 'vertical' }}
            />
            <select
              value={execForm.mode}
              onChange={e => setExecForm({ ...execForm, mode: e.target.value })}
              style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 13 }}
            >
              <option value="full">Full Pipeline</option>
              <option value="fast">Fast Mode</option>
              <option value="reflective">Reflective</option>
              <option value="collaborative">Collaborative</option>
              <option value="learning">Learning</option>
            </select>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowExecute(false)} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={executeTask} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
                {loading ? 'Executing...' : 'Execute'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && metrics && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
            {[
              { label: 'Total Sessions', value: metrics.total_sessions, color: '#2563eb' },
              { label: 'Success Rate', value: `${metrics.success_rate}%`, color: '#059669' },
              { label: 'Avg Time', value: `${metrics.avg_session_time_ms.toFixed(0)}ms`, color: '#7c3aed' },
              { label: 'Active Sessions', value: metrics.active_sessions, color: '#d97706' },
              { label: 'Active Agents', value: metrics.active_agents, color: '#dc2626' },
              { label: 'Events Published', value: metrics.total_events_published, color: '#0891b2' },
              { label: 'Knowledge Shared', value: metrics.total_knowledge_shared, color: '#4f46e5' },
              { label: 'Failed', value: metrics.failed_sessions, color: '#ef4444' },
            ].map((s) => (
              <div key={s.label} style={{ background: '#fff', borderRadius: 12, padding: 16, border: `1px solid ${s.color}20`, textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Phase Distribution */}
          {Object.keys(metrics.phase_distribution).length > 0 && (
            <div style={{ background: '#fff', borderRadius: 12, padding: 16, marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Phase Distribution</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {Object.entries(metrics.phase_distribution).map(([phase, count]) => (
                  <div key={phase} style={{
                    padding: '6px 12px',
                    borderRadius: 6,
                    background: '#f0f9ff',
                    border: '1px solid #bae6fd',
                    fontSize: 12,
                    color: '#0369a1',
                  }}>
                    {phase.replace(/_/g, ' ')}: {count}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sessions Tab */}
      {activeTab === 'sessions' && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Runtime Sessions ({sessions.length})</h3>
          {sessions.length === 0 ? (
            <p style={{ color: '#9ca3af', fontSize: 13 }}>No sessions yet. Execute a task to get started.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {sessions.map((s) => (
                <div key={s.session_id} style={{ padding: '12px', borderRadius: 8, border: '1px solid #e5e7eb', background: s.status === 'completed' ? '#f0fdf4' : s.status === 'failed' ? '#fef2f2' : '#fafafa' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#2563eb' }}>{s.session_id}</span>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: 4,
                      fontSize: 10,
                      fontWeight: 600,
                      background: s.status === 'completed' ? '#dcfce7' : s.status === 'failed' ? '#fecaca' : '#fef3c7',
                      color: s.status === 'completed' ? '#16a34a' : s.status === 'failed' ? '#dc2626' : '#d97706',
                    }}>
                      {s.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#9ca3af' }}>
                    Agent: {s.agent_id} | Mode: {s.mode} | Phases: {s.phases.length}
                  </div>
                  {s.errors.length > 0 && (
                    <div style={{ marginTop: 6, fontSize: 11, color: '#dc2626' }}>
                      Errors: {s.errors.join(', ')}
                    </div>
                  )}
                  {Object.keys(s.phase_timings).length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                      {Object.entries(s.phase_timings).map(([phase, timing]) => (
                        <span key={phase} style={{ padding: '2px 6px', borderRadius: 3, background: '#f3f4f6', fontSize: 10, color: '#6b7280' }}>
                          {phase}: {timing.toFixed(0)}ms
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Activity Tab */}
      {activeTab === 'activity' && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Activity Feed ({activity.length})</h3>
          {activity.length === 0 ? (
            <p style={{ color: '#9ca3af', fontSize: 13 }}>No activity yet. Events will appear here as tasks are executed.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {activity.map((entry) => (
                <div key={entry.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fafafa' }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: entry.type.includes('error') ? '#ef4444' : entry.type.includes('completed') ? '#22c55e' : '#3b82f6',
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>{entry.description}</div>
                    <div style={{ fontSize: 10, color: '#9ca3af' }}>{entry.type} | {entry.agent_id} | {new Date(entry.timestamp).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Subsystems Tab */}
      {activeTab === 'subsystems' && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Subsystem Status</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
            {subsystemStatus.map((sub) => (
              <div key={sub.key} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: 8,
                border: '1px solid #e5e7eb',
                background: subsystemChecks[sub.key] === 'online' ? '#f0fdf4' : subsystemChecks[sub.key] === 'offline' ? '#fef2f2' : '#fafafa',
              }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{sub.name}</span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: 600,
                  background: subsystemChecks[sub.key] === 'online' ? '#dcfce7' : subsystemChecks[sub.key] === 'offline' ? '#fecaca' : '#fef3c7',
                  color: subsystemChecks[sub.key] === 'online' ? '#16a34a' : subsystemChecks[sub.key] === 'offline' ? '#dc2626' : '#d97706',
                }}>
                  {subsystemChecks[sub.key] || 'checking...'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};