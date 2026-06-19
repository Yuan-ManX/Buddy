import React, { useState, useEffect } from 'react';

interface Deployment {
  deployment_id: string;
  name: string;
  status: string;
  target: string;
  url: string;
  port: number;
  container_id: string | null;
  created_at: number;
  started_at: number | null;
  recent_logs: string[];
}

interface DeploymentStats {
  total_deployments: number;
  total_builds: number;
  active_deployments: number;
  deployments: Deployment[];
}

export const DeploymentPanel: React.FC = () => {
  const [stats, setStats] = useState<DeploymentStats | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({ name: 'buddy-app', target: 'local', port: 8080 });
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/deployment/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch deployment stats:', e); }
  };

  const createDeployment = async () => {
    setLoading(true);
    try {
      await fetch('/api/deployment/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      setShowCreate(false);
      fetchStats();
    } catch (e) { console.error('Create failed:', e); }
    setLoading(false);
  };

  const stopDeployment = async (id: string) => {
    await fetch('/api/deployment/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deployment_id: id }),
    });
    fetchStats();
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'running': case 'healthy': return '#16a34a';
      case 'failed': case 'unhealthy': return '#dc2626';
      case 'building': case 'deploying': return '#ca8a04';
      default: return '#888';
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Deployment Pipeline</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Application deployment lifecycle management</p>
        </div>
        <button onClick={() => setShowCreate(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
          + Deploy
        </button>
      </div>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.active_deployments}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.total_builds}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Builds</div>
          </div>
          <div style={{ flex: 1, background: '#fefce8', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#ca8a04' }}>{stats.total_deployments}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Deployments</div>
          </div>
        </div>
      )}

      {showCreate && (
        <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 16, border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>New Deployment</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="App name" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
            <select value={formData.target} onChange={e => setFormData({ ...formData, target: e.target.value })} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }}>
              <option value="local">Local</option>
              <option value="docker">Docker</option>
              <option value="kubernetes">Kubernetes</option>
            </select>
            <input type="number" value={formData.port} onChange={e => setFormData({ ...formData, port: parseInt(e.target.value) })} placeholder="Port" style={{ width: 80, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={createDeployment} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Deploying...' : 'Deploy'}
            </button>
            <button onClick={() => setShowCreate(false)} style={{ padding: '8px 16px', background: '#e5e7eb', color: '#374151', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gap: 12 }}>
        {stats?.deployments?.map(d => (
          <div key={d.deployment_id} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: statusColor(d.status) }} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{d.name}</div>
                  <div style={{ fontSize: 12, color: '#888' }}>{d.target} | {d.url || `port ${d.port}`}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 6, fontSize: 11, color: statusColor(d.status) }}>{d.status}</span>
                {(d.status === 'running' || d.status === 'healthy') && (
                  <button onClick={() => stopDeployment(d.deployment_id)} style={{ padding: '4px 12px', background: '#fef2f2', color: '#dc2626', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>Stop</button>
                )}
              </div>
            </div>
            {d.recent_logs && d.recent_logs.length > 0 && (
              <div style={{ marginTop: 8, background: '#1e1e1e', borderRadius: 8, padding: 8, maxHeight: 120, overflow: 'auto' }}>
                {d.recent_logs.map((log, i) => (
                  <div key={i} style={{ fontSize: 11, color: '#d4d4d4', fontFamily: 'monospace' }}>{log}</div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};