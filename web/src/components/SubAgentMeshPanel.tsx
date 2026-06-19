import React, { useState, useEffect } from 'react';

interface MeshStats {
  total_tasks: number;
  total_tokens: number;
  max_workers: number;
  pool_status: { pool_size: number; available: number; in_use: number; total: number };
  workstream_stats: { total_workstreams: number; active: number; completed: number; failed: number; pending: number };
  recent_dispatches: { workstream_id: string; task: string; workers: number; elapsed_ms: number; tokens: number; success: boolean }[];
}

interface Workstream {
  workstream_id: string;
  name: string;
  status: string;
  task_count: number;
  aggregation: string;
  created_at: string;
  completed_at: string | null;
}

export const SubAgentMeshPanel: React.FC = () => {
  const [stats, setStats] = useState<MeshStats | null>(null);
  const [workstreams, setWorkstreams] = useState<Workstream[]>([]);
  const [dispatchTask, setDispatchTask] = useState('');
  const [numWorkers, setNumWorkers] = useState(3);
  const [dispatchResult, setDispatchResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchWorkstreams();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/subagent-mesh/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch mesh stats:', e); }
  };

  const fetchWorkstreams = async () => {
    try {
      const res = await fetch('/api/subagent-mesh/workstreams');
      const data = await res.json();
      setWorkstreams(data.workstreams || []);
    } catch (e) { console.error('Failed to fetch workstreams:', e); }
  };

  const runDispatch = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/subagent-mesh/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: dispatchTask, num_workers: numWorkers, aggregation: 'merge' }),
      });
      const data = await res.json();
      setDispatchResult(data);
      fetchStats();
      fetchWorkstreams();
    } catch (e) { console.error('Dispatch failed:', e); }
    setLoading(false);
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#22c55e';
      case 'running': return '#3b82f6';
      case 'failed': return '#ef4444';
      case 'pending': return '#f59e0b';
      case 'cancelled': return '#94a3b8';
      default: return '#94a3b8';
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>SubAgent Mesh</h2>
        <span className="panel-subtitle">Parallel sub-agent orchestration</span>
      </div>

      <div className="panel-content">
        {/* Stats */}
        {stats && (
          <>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{stats.total_tasks}</div>
                <div className="stat-label">Total Tasks</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{stats.total_tokens.toLocaleString()}</div>
                <div className="stat-label">Tokens</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{stats.max_workers}</div>
                <div className="stat-label">Max Workers</div>
              </div>
            </div>

            {/* Pool Status */}
            <div className="section">
              <h3>Pool Status</h3>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{stats.pool_status.available}</div>
                  <div className="stat-label">Available</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.pool_status.in_use}</div>
                  <div className="stat-label">In Use</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.pool_status.pool_size}</div>
                  <div className="stat-label">Pool Size</div>
                </div>
              </div>
            </div>

            {/* Workstream Stats */}
            <div className="section">
              <h3>Workstreams</h3>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{stats.workstream_stats.total_workstreams}</div>
                  <div className="stat-label">Total</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: '#3b82f6' }}>{stats.workstream_stats.active}</div>
                  <div className="stat-label">Active</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: '#22c55e' }}>{stats.workstream_stats.completed}</div>
                  <div className="stat-label">Completed</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color: '#ef4444' }}>{stats.workstream_stats.failed}</div>
                  <div className="stat-label">Failed</div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Dispatch */}
        <div className="section">
          <h3>Dispatch Task</h3>
          <div className="input-row">
            <input
              className="text-input"
              placeholder="Task description..."
              value={dispatchTask}
              onChange={e => setDispatchTask(e.target.value)}
            />
            <input
              className="text-input"
              type="number"
              min={1}
              max={10}
              value={numWorkers}
              onChange={e => setNumWorkers(parseInt(e.target.value))}
              style={{ width: 80 }}
            />
            <button className="btn btn-primary" onClick={runDispatch} disabled={loading || !dispatchTask}>
              {loading ? 'Dispatching...' : 'Dispatch'}
            </button>
          </div>
        </div>

        {/* Dispatch Result */}
        {dispatchResult && (
          <div className="section">
            <h3>Result</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{dispatchResult.num_workers}</div>
                <div className="stat-label">Workers</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{dispatchResult.elapsed_ms}ms</div>
                <div className="stat-label">Elapsed</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{dispatchResult.total_tokens}</div>
                <div className="stat-label">Tokens</div>
              </div>
            </div>

            {dispatchResult.results && (
              <div className="list">
                {dispatchResult.results.map((r: any, i: number) => (
                  <div key={r.agent_id} className="list-item">
                    <div className="list-item-header">
                      <span>Worker {i + 1}</span>
                      <span className="badge" style={{ background: r.status === 'completed' ? '#22c55e' : '#ef4444' }}>
                        {r.status}
                      </span>
                    </div>
                    <div className="list-item-meta">
                      <span>{r.tokens} tokens</span>
                    </div>
                    <div className="result-text">{r.result?.substring(0, 300)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Workstreams List */}
        <div className="section">
          <h3>Workstreams ({workstreams.length})</h3>
          <div className="list">
            {workstreams.map(ws => (
              <div key={ws.workstream_id} className="list-item">
                <div className="list-item-header">
                  <span className="list-item-name">{ws.name}</span>
                  <span className="badge" style={{ background: statusColor(ws.status) }}>
                    {ws.status}
                  </span>
                </div>
                <div className="list-item-meta">
                  <span>{ws.task_count} tasks</span>
                  <span>Strategy: {ws.aggregation}</span>
                  <span>{new Date(ws.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};