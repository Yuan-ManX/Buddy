import React, { useState, useEffect } from 'react';

interface AgentInfo {
  agent_id: string;
  name: string;
  description: string;
  capabilities: string[];
  tool_set: string[];
  model_id: string;
  current_load: number;
}

interface WorkstreamInfo {
  workstream_id: string;
  workstream_type: string;
  description: string;
  assigned_agent_id: string | null;
  status: string;
  priority: number;
  result: any;
  created_at: number;
}

interface SquadInfo {
  squad_id: string;
  name: string;
  leader_id: string;
  member_count: number;
  active_workstreams: number;
}

interface OrchestratorStats {
  total_agents: number;
  total_workstreams: number;
  total_completed: number;
  total_failed: number;
  active_workstreams: number;
  total_squads: number;
  agents: AgentInfo[];
  squads: SquadInfo[];
  workstreams_by_status: Record<string, number>;
}

export const AgentOrchestratorPanel: React.FC = () => {
  const [stats, setStats] = useState<OrchestratorStats | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [workstreams, setWorkstreams] = useState<WorkstreamInfo[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showSquad, setShowSquad] = useState(false);
  const [formData, setFormData] = useState({ workstream_type: 'general', description: '', priority: 5 });
  const [squadForm, setSquadForm] = useState({ name: '', description: '', leader_agent_id: '', member_agent_ids: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchAgents();
    fetchWorkstreams();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/agent-orchestrator/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch orchestrator stats:', e); }
  };

  const fetchAgents = async () => {
    try {
      const res = await fetch('/api/agent-orchestrator/agents');
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (e) { console.error('Failed to fetch agents:', e); }
  };

  const fetchWorkstreams = async () => {
    try {
      const res = await fetch('/api/agent-orchestrator/workstreams');
      const data = await res.json();
      setWorkstreams(data.workstreams || []);
    } catch (e) { console.error('Failed to fetch workstreams:', e); }
  };

  const createWorkstream = async () => {
    setLoading(true);
    try {
      await fetch('/api/agent-orchestrator/create-workstream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      setShowCreate(false);
      setFormData({ workstream_type: 'general', description: '', priority: 5 });
      fetchStats();
      fetchWorkstreams();
    } catch (e) { console.error('Create failed:', e); }
    setLoading(false);
  };

  const autoAssign = async (workstreamId: string) => {
    await fetch('/api/agent-orchestrator/auto-assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workstream_id: workstreamId }),
    });
    fetchWorkstreams();
  };

  const executeWorkstream = async (workstreamId: string) => {
    await fetch('/api/agent-orchestrator/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workstream_id: workstreamId }),
    });
    fetchWorkstreams();
    fetchStats();
  };

  const createSquad = async () => {
    setLoading(true);
    try {
      await fetch('/api/agent-orchestrator/create-squad', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...squadForm,
          member_agent_ids: squadForm.member_agent_ids.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowSquad(false);
      setSquadForm({ name: '', description: '', leader_agent_id: '', member_agent_ids: '' });
      fetchStats();
    } catch (e) { console.error('Create squad failed:', e); }
    setLoading(false);
  };

  const statusColor = (status: string) => {
    const colors: Record<string, string> = {
      idle: '#9ca3af', enqueued: '#f59e0b', claimed: '#3b82f6',
      executing: '#8b5cf6', reviewing: '#06b6d4', completed: '#16a34a',
      failed: '#ef4444', blocked: '#dc2626',
    };
    return colors[status] || '#9ca3af';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Agent Orchestrator</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Multi-agent coordination with parallel workstreams and squad-based routing</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setShowSquad(true)} style={{ padding: '8px 16px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            + New Squad
          </button>
          <button onClick={() => setShowCreate(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            + New Workstream
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_agents}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Agents</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_workstreams}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Workstreams</div>
          </div>
          <div style={{ flex: 1, background: '#fef3c7', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#d97706' }}>{stats.active_workstreams}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active</div>
          </div>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.total_completed}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Completed</div>
          </div>
          <div style={{ flex: 1, background: '#fef2f2', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#ef4444' }}>{stats.total_failed}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Failed</div>
          </div>
        </div>
      )}

      {/* Create Workstream Form */}
      {showCreate && (
        <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 16, border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Create New Workstream</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <select value={formData.workstream_type} onChange={e => setFormData({ ...formData, workstream_type: e.target.value })} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }}>
              <option value="general">General</option>
              <option value="code_generation">Code Generation</option>
              <option value="code_review">Code Review</option>
              <option value="research">Research</option>
              <option value="analysis">Analysis</option>
              <option value="deployment">Deployment</option>
              <option value="testing">Testing</option>
              <option value="documentation">Documentation</option>
            </select>
            <input type="number" value={formData.priority} onChange={e => setFormData({ ...formData, priority: Number(e.target.value) })} min={1} max={10} style={{ width: 80, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} placeholder="Priority" />
          </div>
          <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} placeholder="Workstream description" rows={2} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', resize: 'vertical', marginBottom: 8 }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={createWorkstream} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Creating...' : 'Create'}
            </button>
            <button onClick={() => setShowCreate(false)} style={{ padding: '8px 16px', background: '#e5e7eb', color: '#374151', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Create Squad Form */}
      {showSquad && (
        <div style={{ background: '#faf5ff', borderRadius: 12, padding: 16, marginBottom: 16, border: '1px solid #e9d5ff' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Create New Squad</h3>
          <input value={squadForm.name} onChange={e => setSquadForm({ ...squadForm, name: e.target.value })} placeholder="Squad name" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', marginBottom: 8 }} />
          <input value={squadForm.description} onChange={e => setSquadForm({ ...squadForm, description: e.target.value })} placeholder="Squad description" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', marginBottom: 8 }} />
          <select value={squadForm.leader_agent_id} onChange={e => setSquadForm({ ...squadForm, leader_agent_id: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', marginBottom: 8 }}>
            <option value="">Select leader agent</option>
            {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.name}</option>)}
          </select>
          <input value={squadForm.member_agent_ids} onChange={e => setSquadForm({ ...squadForm, member_agent_ids: e.target.value })} placeholder="Member agent IDs (comma-separated)" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', marginBottom: 8 }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={createSquad} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Creating...' : 'Create Squad'}
            </button>
            <button onClick={() => setShowSquad(false)} style={{ padding: '8px 16px', background: '#e5e7eb', color: '#374151', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Agent Cards */}
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Registered Agents</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12, marginBottom: 24 }}>
        {agents.map(agent => (
          <div key={agent.agent_id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{agent.name}</div>
              <span style={{ fontSize: 11, color: agent.current_load > 0 ? '#f59e0b' : '#16a34a', background: agent.current_load > 0 ? '#fef3c7' : '#f0fdf4', padding: '2px 8px', borderRadius: 6 }}>
                {agent.current_load > 0 ? `${agent.current_load} active` : 'Idle'}
              </span>
            </div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>{agent.description}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {agent.capabilities.map(c => (
                <span key={c} style={{ fontSize: 10, padding: '2px 6px', background: '#eff6ff', color: '#2563eb', borderRadius: 4 }}>{c}</span>
              ))}
            </div>
            <div style={{ marginTop: 8, fontSize: 11, color: '#888' }}>
              {agent.tool_set.length} tools · Model: {agent.model_id}
            </div>
          </div>
        ))}
      </div>

      {/* Workstreams */}
      <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Workstreams ({workstreams.length})</h3>
      <div style={{ display: 'grid', gap: 8 }}>
        {workstreams.map(ws => (
          <div key={ws.workstream_id} style={{ background: '#fff', borderRadius: 12, padding: 12, border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ background: statusColor(ws.status), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11, textTransform: 'uppercase' }}>{ws.status}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, fontSize: 13 }}>{ws.description}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{ws.workstream_type} · Priority: {ws.priority} · {ws.assigned_agent_id || 'Unassigned'}</div>
            </div>
            {ws.status === 'idle' && (
              <button onClick={() => autoAssign(ws.workstream_id)} style={{ padding: '4px 12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                Auto Assign
              </button>
            )}
            {ws.status === 'enqueued' && (
              <button onClick={() => executeWorkstream(ws.workstream_id)} style={{ padding: '4px 12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                Execute
              </button>
            )}
            {ws.result && <div style={{ fontSize: 11, color: '#16a34a' }}>Done</div>}
          </div>
        ))}
      </div>
    </div>
  );
};