import React, { useState, useEffect } from 'react';

interface FleetStats {
  total_agents: number;
  overall_health: string;
  healthy_agents: number;
  degraded_agents: number;
  offline_agents: number;
  average_health_score: number;
  total_tasks_processed: number;
  total_load: number;
  total_capacity: number;
  load_percentage: number;
  available_agents: number;
  agents: FleetAgentInfo[];
  issues: string[];
  recommendations: string[];
}

interface FleetAgentInfo {
  agent_id: string;
  agent_name: string;
  role: string;
  status: string;
  current_load: number;
  health_score: number;
  success_rate: number;
  avg_response_time_ms: number;
  capabilities: string[];
}

export const FleetPanel: React.FC = () => {
  const [stats, setStats] = useState<FleetStats | null>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [formData, setFormData] = useState({
    agent_id: '', agent_name: '', role: 'worker', capabilities: '', max_concurrent: 5, tags: '',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);
  const fetchStats = async () => {
    try {
      const res = await fetch('/api/fleet/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch fleet stats:', e); }
  };

  const registerAgent = async () => {
    setLoading(true);
    try {
      await fetch('/api/fleet/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          capabilities: formData.capabilities.split(',').map(s => s.trim()).filter(Boolean),
          tags: formData.tags.split(',').map(s => s.trim()).filter(Boolean),
        }),
      });
      setShowRegister(false);
      setFormData({ agent_id: '', agent_name: '', role: 'worker', capabilities: '', max_concurrent: 5, tags: '' });
      fetchStats();
    } catch (e) { console.error('Register failed:', e); }
    setLoading(false);
  };

  const sendHeartbeat = async (agentId: string) => {
    await fetch('/api/fleet/heartbeat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId, load: 0 }),
    });
    fetchStats();
  };

  const healthColor = (health: string) => {
    const map: Record<string, string> = { healthy: '#16a34a', degraded: '#f59e0b', critical: '#ef4444', offline: '#6b7280' };
    return map[health] || '#6b7280';
  };

  const statusColor = (status: string) => {
    const map: Record<string, string> = { online: '#16a34a', busy: '#f59e0b', idle: '#3b82f6', degraded: '#ef4444', offline: '#6b7280', recovering: '#8b5cf6' };
    return map[status] || '#6b7280';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Agent Fleet</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Fleet-wide health monitoring, load balancing, and task assignment</p>
        </div>
        <button onClick={() => setShowRegister(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
          + Register Agent
        </button>
      </div>

      {stats && (
        <>
          {/* Health Overview */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: healthColor(stats.overall_health) }}>{stats.overall_health.toUpperCase()}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Fleet Health</div>
            </div>
            <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.healthy_agents}/{stats.total_agents}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Healthy Agents</div>
            </div>
            <div style={{ flex: 1, background: '#fef3c7', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#d97706' }}>{stats.load_percentage}%</div>
              <div style={{ fontSize: 12, color: '#666' }}>Load ({stats.total_load}/{stats.total_capacity})</div>
            </div>
            <div style={{ flex: 1, background: '#faf5ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{stats.total_tasks_processed}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Tasks Processed</div>
            </div>
            <div style={{ flex: 1, background: stats.offline_agents > 0 ? '#fef2f2' : '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: stats.offline_agents > 0 ? '#ef4444' : '#16a34a' }}>{stats.offline_agents}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Offline</div>
            </div>
          </div>

          {/* Issues & Recommendations */}
          {(stats.issues.length > 0 || stats.recommendations.length > 0) && (
            <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
              {stats.issues.length > 0 && (
                <div style={{ flex: 1, background: '#fef2f2', borderRadius: 12, padding: 16, border: '1px solid #fecaca' }}>
                  <h4 style={{ fontSize: 13, fontWeight: 600, color: '#ef4444', marginBottom: 8 }}>Issues</h4>
                  {stats.issues.map((issue, i) => (
                    <div key={i} style={{ fontSize: 12, color: '#dc2626', padding: '2px 0' }}>{issue}</div>
                  ))}
                </div>
              )}
              {stats.recommendations.length > 0 && (
                <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, border: '1px solid #bfdbfe' }}>
                  <h4 style={{ fontSize: 13, fontWeight: 600, color: '#2563eb', marginBottom: 8 }}>Recommendations</h4>
                  {stats.recommendations.map((rec, i) => (
                    <div key={i} style={{ fontSize: 12, color: '#1d4ed8', padding: '2px 0' }}>{rec}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Agent Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {stats.agents.map(agent => (
              <div key={agent.agent_id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{agent.agent_name}</div>
                    <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#888' }}>{agent.agent_id}</div>
                  </div>
                  <span style={{ background: statusColor(agent.status), color: '#fff', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{agent.status}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12, color: '#666', marginBottom: 8 }}>
                  <div>Role: <strong>{agent.role}</strong></div>
                  <div>Load: <strong>{agent.current_load}</strong></div>
                  <div>Health: <strong>{(agent.health_score * 100).toFixed(0)}%</strong></div>
                  <div>Success: <strong>{(agent.success_rate * 100).toFixed(0)}%</strong></div>
                  <div>Response: <strong>{agent.avg_response_time_ms}ms</strong></div>
                </div>
                {agent.capabilities.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                    {agent.capabilities.map(cap => (
                      <span key={cap} style={{ background: '#eff6ff', color: '#2563eb', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{cap}</span>
                    ))}
                  </div>
                )}
                <button onClick={() => sendHeartbeat(agent.agent_id)} style={{ width: '100%', padding: '6px', background: '#f3f4f6', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                  Send Heartbeat
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Register Modal */}
      {showRegister && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', borderRadius: 16, padding: 24, width: 450 }}>
            <h3 style={{ marginBottom: 16 }}>Register Fleet Agent</h3>
            <div style={{ display: 'grid', gap: 10 }}>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Agent ID</label><input value={formData.agent_id} onChange={e => setFormData({ ...formData, agent_id: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Agent Name</label><input value={formData.agent_name} onChange={e => setFormData({ ...formData, agent_name: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Role</label><input value={formData.role} onChange={e => setFormData({ ...formData, role: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Capabilities (comma-separated)</label><input value={formData.capabilities} onChange={e => setFormData({ ...formData, capabilities: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Max Concurrent</label><input type="number" value={formData.max_concurrent} onChange={e => setFormData({ ...formData, max_concurrent: parseInt(e.target.value) })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
              <div><label style={{ fontSize: 12, display: 'block', marginBottom: 2 }}>Tags (comma-separated)</label><input value={formData.tags} onChange={e => setFormData({ ...formData, tags: e.target.value })} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db' }} /></div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button onClick={() => setShowRegister(false)} style={{ padding: '8px 16px', background: '#e5e7eb', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
              <button onClick={registerAgent} disabled={loading} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>{loading ? 'Registering...' : 'Register'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};