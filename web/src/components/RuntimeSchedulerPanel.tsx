import React, { useState, useEffect, useCallback } from 'react';

const BASE_URL = '/api';
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try { const parsed = JSON.parse(body); message = parsed.detail || parsed.error || body; } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

type Tab = 'Overview' | 'Queue' | 'Dependencies' | 'Quotas' | 'Schedule';

export const RuntimeSchedulerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('Overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview tab state
  const [stats, setStats] = useState<any>(null);

  // Queue tab state
  const [queueTasks, setQueueTasks] = useState<any[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [enqueueForm, setEnqueueForm] = useState({
    priority: 'medium',
    agent_id: '',
    payload: '',
  });

  // Dependencies tab state
  const [dependencies, setDependencies] = useState<any[]>([]);
  const [depsLoading, setDepsLoading] = useState(false);
  const [depForm, setDepForm] = useState({ task_id: '', depends_on: '' });

  // Quotas tab state
  const [quotaResult, setQuotaResult] = useState<any>(null);
  const [quotaForm, setQuotaForm] = useState({ resource: '', limit: 10, scope: '' });
  const [quotaCheck, setQuotaCheck] = useState({ resource: '', scope: '' });

  // Schedule tab state
  const [schedule, setSchedule] = useState<any>(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);

  // Dark theme colors
  const colors = {
    bg: '#1a1a2e',
    card: '#16213e',
    border: '#2a2a4a',
    text: '#e0e0e0',
    accent: '#7c3aed',
    textSecondary: '#a0a0b0',
    green: '#10b981',
    red: '#ef4444',
    yellow: '#f59e0b',
    blue: '#3b82f6',
  };

  const inputStyle: React.CSSProperties = {
    padding: '8px 12px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    background: colors.bg,
    color: colors.text,
    fontSize: '14px',
    width: '100%',
    boxSizing: 'border-box',
  };

  const btnPrimary: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    background: colors.accent,
    color: '#fff',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  };

  const btnSecondary: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    background: colors.card,
    color: colors.text,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  };

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '8px 16px',
    border: 'none',
    borderRadius: '8px',
    background: activeTab === tab ? colors.accent : colors.card,
    color: activeTab === tab ? '#fff' : colors.textSecondary,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    transition: 'all 0.15s',
  });

  // Load overview stats
  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<any>('/runtime-scheduler/stats');
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load queue tasks
  const loadQueue = useCallback(async () => {
    try {
      setQueueLoading(true);
      const data = await request<any>('/runtime-scheduler/queue');
      setQueueTasks(data.tasks || data || []);
    } catch (err: any) {
      alert('Failed to load queue: ' + err.message);
    } finally {
      setQueueLoading(false);
    }
  }, []);

  // Load dependencies
  const loadDependencies = useCallback(async () => {
    try {
      setDepsLoading(true);
      const data = await request<any>('/runtime-scheduler/dependencies');
      setDependencies(data.dependencies || data || []);
    } catch (err: any) {
      alert('Failed to load dependencies: ' + err.message);
    } finally {
      setDepsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadQueue();
    loadDependencies();
  }, [loadStats, loadQueue, loadDependencies]);

  // Enqueue task
  const handleEnqueue = useCallback(async () => {
    if (!enqueueForm.payload.trim()) {
      alert('Payload is required');
      return;
    }
    try {
      await request<any>('/runtime-scheduler/queue', {
        method: 'POST',
        body: JSON.stringify({
          priority: enqueueForm.priority,
          agent_id: enqueueForm.agent_id || undefined,
          payload: enqueueForm.payload,
        }),
      });
      setEnqueueForm({ priority: 'medium', agent_id: '', payload: '' });
      loadQueue();
      loadStats();
    } catch (err: any) {
      alert('Failed to enqueue task: ' + err.message);
    }
  }, [enqueueForm, loadQueue, loadStats]);

  // Dequeue task
  const handleDequeue = useCallback(async (taskId: string) => {
    try {
      await request<any>(`/runtime-scheduler/queue/${taskId}/dequeue`, { method: 'POST' });
      loadQueue();
      loadStats();
    } catch (err: any) {
      alert('Failed to dequeue task: ' + err.message);
    }
  }, [loadQueue, loadStats]);

  // Complete task
  const handleComplete = useCallback(async (taskId: string) => {
    try {
      await request<any>(`/runtime-scheduler/queue/${taskId}/complete`, { method: 'POST' });
      loadQueue();
      loadStats();
    } catch (err: any) {
      alert('Failed to complete task: ' + err.message);
    }
  }, [loadQueue, loadStats]);

  // Fail task
  const handleFail = useCallback(async (taskId: string) => {
    try {
      await request<any>(`/runtime-scheduler/queue/${taskId}/fail`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Manual failure' }),
      });
      loadQueue();
      loadStats();
    } catch (err: any) {
      alert('Failed to mark task as failed: ' + err.message);
    }
  }, [loadQueue, loadStats]);

  // Add dependency
  const handleAddDependency = useCallback(async () => {
    if (!depForm.task_id.trim() || !depForm.depends_on.trim()) {
      alert('Task ID and depends_on are required');
      return;
    }
    try {
      await request<any>('/runtime-scheduler/dependencies', {
        method: 'POST',
        body: JSON.stringify(depForm),
      });
      setDepForm({ task_id: '', depends_on: '' });
      loadDependencies();
    } catch (err: any) {
      alert('Failed to add dependency: ' + err.message);
    }
  }, [depForm, loadDependencies]);

  // Resolve dependency
  const handleResolveDependency = useCallback(async (depId: string) => {
    try {
      await request<any>(`/runtime-scheduler/dependencies/${depId}/resolve`, { method: 'POST' });
      loadDependencies();
    } catch (err: any) {
      alert('Failed to resolve dependency: ' + err.message);
    }
  }, [loadDependencies]);

  // Set quota
  const handleSetQuota = useCallback(async () => {
    if (!quotaForm.resource.trim()) {
      alert('Resource name is required');
      return;
    }
    try {
      const data = await request<any>('/runtime-scheduler/quotas', {
        method: 'POST',
        body: JSON.stringify(quotaForm),
      });
      setQuotaResult(data);
      setQuotaForm({ resource: '', limit: 10, scope: '' });
    } catch (err: any) {
      alert('Failed to set quota: ' + err.message);
    }
  }, [quotaForm]);

  // Check quota
  const handleCheckQuota = useCallback(async () => {
    if (!quotaCheck.resource.trim()) {
      alert('Resource name is required');
      return;
    }
    try {
      const params = new URLSearchParams();
      params.set('resource', quotaCheck.resource);
      if (quotaCheck.scope) params.set('scope', quotaCheck.scope);
      const data = await request<any>(`/runtime-scheduler/quotas/check?${params.toString()}`);
      setQuotaResult(data);
    } catch (err: any) {
      alert('Failed to check quota: ' + err.message);
    }
  }, [quotaCheck]);

  // Get schedule
  const handleGetSchedule = useCallback(async () => {
    try {
      setScheduleLoading(true);
      const data = await request<any>('/runtime-scheduler/schedule');
      setSchedule(data);
    } catch (err: any) {
      alert('Failed to get schedule: ' + err.message);
    } finally {
      setScheduleLoading(false);
    }
  }, []);

  // Optimize schedule
  const handleOptimizeSchedule = useCallback(async () => {
    try {
      setScheduleLoading(true);
      const data = await request<any>('/runtime-scheduler/schedule/optimize', { method: 'POST' });
      setSchedule(data);
    } catch (err: any) {
      alert('Failed to optimize schedule: ' + err.message);
    } finally {
      setScheduleLoading(false);
    }
  }, []);

  const priorityColor = (p: string): string => {
    switch (p) {
      case 'high': return colors.red;
      case 'medium': return colors.yellow;
      case 'low': return colors.green;
      default: return colors.textSecondary;
    }
  };

  const statusColor = (s: string): string => {
    switch (s) {
      case 'pending': return colors.yellow;
      case 'running': return colors.blue;
      case 'completed': return colors.green;
      case 'failed': return colors.red;
      case 'blocked': return colors.red;
      default: return colors.textSecondary;
    }
  };

  if (loading) {
    return (
      <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
        <div className="panel-header">
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Runtime Scheduler</h2>
          <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>Task queue, dependencies, quotas, and schedule management</p>
        </div>
        <div className="panel-loading" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
          <span style={{ color: colors.textSecondary }}>Loading runtime scheduler data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ padding: '24px', background: colors.bg, minHeight: '100vh', color: colors.text }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Runtime Scheduler</h2>
        <p className="panel-subtitle" style={{ color: colors.textSecondary, margin: '4px 0 0' }}>
          Task queue, dependencies, quotas, and schedule management
        </p>
        {error && (
          <div className="error-banner" style={{ padding: '10px 16px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', color: colors.red, marginTop: '8px', fontSize: '14px' }}>
            {error}
            <button onClick={() => { setError(null); loadStats(); }} style={{ marginLeft: '8px', background: 'none', border: 'none', color: colors.red, cursor: 'pointer', fontWeight: 600 }}>Dismiss</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar" style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' as const }}>
          {[
            { label: 'Total Tasks', value: stats.total_tasks ?? stats.total ?? '0', color: colors.accent },
            { label: 'Pending', value: stats.pending ?? stats.pending_tasks ?? '0', color: colors.yellow },
            { label: 'Running', value: stats.running ?? stats.active_tasks ?? '0', color: colors.blue },
            { label: 'Completed', value: stats.completed ?? stats.completed_tasks ?? '0', color: colors.green },
            { label: 'Failed', value: stats.failed ?? stats.failed_tasks ?? '0', color: colors.red },
          ].map((stat) => (
            <div key={stat.label} className="stat-item" style={{
              flex: '1 1 120px', minWidth: '120px', background: colors.card,
              border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '14px 18px',
              display: 'flex', alignItems: 'center', gap: '12px',
            }}>
              <div className="stat-content" style={{ display: 'flex', flexDirection: 'column' }}>
                <span className="stat-value" style={{ fontSize: '1.3rem', fontWeight: 800, color: colors.text }}>{stat.value}</span>
                <span className="stat-label" style={{ fontSize: '0.72rem', color: colors.textSecondary, fontWeight: 600 }}>{stat.label}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {(['Overview', 'Queue', 'Dependencies', 'Quotas', 'Schedule'] as Tab[]).map((tab) => (
          <button key={tab} className={`forge-tab ${activeTab === tab ? 'active' : ''}`}
            style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'Overview' && stats && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Overview</h3>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Total Tasks</span>
            <strong>{stats.total_tasks ?? stats.total ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Pending</span>
            <strong style={{ color: colors.yellow }}>{stats.pending ?? stats.pending_tasks ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Running</span>
            <strong style={{ color: colors.blue }}>{stats.running ?? stats.active_tasks ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Completed</span>
            <strong style={{ color: colors.green }}>{stats.completed ?? stats.completed_tasks ?? 'N/A'}</strong>
          </div>
          <div className="dashboard-stat-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}` }}>
            <span style={{ color: colors.textSecondary }}>Failed</span>
            <strong style={{ color: colors.red }}>{stats.failed ?? stats.failed_tasks ?? 'N/A'}</strong>
          </div>
          <div style={{ marginTop: '16px' }}>
            <button onClick={loadStats} style={btnSecondary}>Refresh Stats</button>
          </div>
        </div>
      )}

      {/* Queue Tab */}
      {activeTab === 'Queue' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Task Queue</h3>

          {/* Enqueue form */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Enqueue New Task</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select value={enqueueForm.priority}
                  onChange={(e) => setEnqueueForm({ ...enqueueForm, priority: e.target.value })}
                  style={{ ...inputStyle, flex: 1 }}>
                  <option value="low">Low Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="high">High Priority</option>
                </select>
                <input type="text" value={enqueueForm.agent_id}
                  onChange={(e) => setEnqueueForm({ ...enqueueForm, agent_id: e.target.value })}
                  placeholder="Agent ID (optional)" style={{ ...inputStyle, flex: 1 }} />
              </div>
              <textarea value={enqueueForm.payload}
                onChange={(e) => setEnqueueForm({ ...enqueueForm, payload: e.target.value })}
                placeholder="Task payload..."
                rows={3}
                style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }} />
              <button onClick={handleEnqueue} style={btnPrimary}>Enqueue Task</button>
            </div>
          </div>

          {/* Queue list */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>Tasks ({queueTasks.length})</span>
              <button onClick={loadQueue} style={{ ...btnSecondary, fontSize: '12px', padding: '4px 12px' }}>Refresh</button>
            </div>
            {queueTasks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {queueLoading ? 'Loading tasks...' : 'No tasks in queue'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {queueTasks.map((task: any, idx: number) => {
                  const taskId = task.id || task.task_id || `task-${idx}`;
                  const status = task.status || 'pending';
                  const priority = task.priority || 'medium';
                  return (
                    <div key={taskId} className="forge-skill-card"
                      style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                        border: `1px solid ${colors.border}`,
                      }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{
                            padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
                            background: priorityColor(priority) + '22', color: priorityColor(priority),
                            fontWeight: 600, textTransform: 'uppercase',
                          }}>{priority}</span>
                          <span style={{
                            padding: '2px 8px', borderRadius: '4px', fontSize: '11px',
                            background: statusColor(status) + '22', color: statusColor(status),
                            fontWeight: 600, textTransform: 'capitalize',
                          }}>{status}</span>
                          <span style={{ fontWeight: 600, fontSize: '13px' }}>{taskId}</span>
                        </div>
                        {task.payload && (
                          <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '400px' }}>
                            {typeof task.payload === 'string' ? task.payload.slice(0, 80) : JSON.stringify(task.payload).slice(0, 80)}
                          </div>
                        )}
                        {task.agent_id && (
                          <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '2px' }}>Agent: {task.agent_id}</div>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        {status === 'pending' && (
                          <>
                            <button onClick={() => handleDequeue(taskId)}
                              style={{ ...btnSecondary, fontSize: '11px', padding: '4px 8px', color: colors.yellow, borderColor: colors.yellow }}>
                              Dequeue
                            </button>
                            <button onClick={() => handleComplete(taskId)}
                              style={{ ...btnSecondary, fontSize: '11px', padding: '4px 8px', color: colors.green, borderColor: colors.green }}>
                              Complete
                            </button>
                          </>
                        )}
                        {status === 'running' && (
                          <button onClick={() => handleFail(taskId)}
                            style={{ ...btnSecondary, fontSize: '11px', padding: '4px 8px', color: colors.red, borderColor: colors.red }}>
                            Fail
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dependencies Tab */}
      {activeTab === 'Dependencies' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Task Dependencies</h3>

          {/* Add dependency */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Add Dependency</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={depForm.task_id}
                onChange={(e) => setDepForm({ ...depForm, task_id: e.target.value })}
                placeholder="Task ID" style={{ ...inputStyle, flex: 1 }} />
              <input type="text" value={depForm.depends_on}
                onChange={(e) => setDepForm({ ...depForm, depends_on: e.target.value })}
                placeholder="Depends On (task ID)" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={handleAddDependency} style={btnPrimary}>Add</button>
            </div>
          </div>

          {/* Dependencies list */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600 }}>Dependencies ({dependencies.length})</span>
              <button onClick={loadDependencies} style={{ ...btnSecondary, fontSize: '12px', padding: '4px 12px' }}>Refresh</button>
            </div>
            {dependencies.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
                {depsLoading ? 'Loading dependencies...' : 'No dependencies configured'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {dependencies.map((dep: any, idx: number) => (
                  <div key={dep.id || dep.dep_id || idx} className="forge-skill-card"
                    style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 16px', background: colors.bg, borderRadius: '10px',
                      border: `1px solid ${colors.border}`,
                    }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>
                        {dep.task_id} → {dep.depends_on}
                      </div>
                      <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '2px' }}>
                        Status: <span style={{ color: dep.resolved ? colors.green : colors.yellow }}>
                          {dep.resolved ? 'Resolved' : 'Pending'}
                        </span>
                      </div>
                    </div>
                    {!dep.resolved && (
                      <button onClick={() => handleResolveDependency(dep.id || dep.dep_id)}
                        style={{ ...btnSecondary, fontSize: '12px', padding: '4px 12px', color: colors.green, borderColor: colors.green }}>
                        Resolve
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quotas Tab */}
      {activeTab === 'Quotas' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Resource Quotas</h3>

          {/* Set quota */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Set Quota</h4>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input type="text" value={quotaForm.resource}
                onChange={(e) => setQuotaForm({ ...quotaForm, resource: e.target.value })}
                placeholder="Resource (e.g. cpu, memory, tokens)" style={{ ...inputStyle, flex: 1 }} />
              <input type="number" value={quotaForm.limit} min={1}
                onChange={(e) => setQuotaForm({ ...quotaForm, limit: parseInt(e.target.value) || 10 })}
                style={{ ...inputStyle, width: '100px' }} />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={quotaForm.scope}
                onChange={(e) => setQuotaForm({ ...quotaForm, scope: e.target.value })}
                placeholder="Scope (e.g. agent-id, global)" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={handleSetQuota} style={btnPrimary}>Set Quota</button>
            </div>
          </div>

          {/* Check quota */}
          <div style={{ background: colors.bg, borderRadius: '8px', padding: '16px', marginBottom: '16px', border: `1px solid ${colors.border}` }}>
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600 }}>Check Quota</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input type="text" value={quotaCheck.resource}
                onChange={(e) => setQuotaCheck({ ...quotaCheck, resource: e.target.value })}
                placeholder="Resource name" style={{ ...inputStyle, flex: 1 }} />
              <input type="text" value={quotaCheck.scope}
                onChange={(e) => setQuotaCheck({ ...quotaCheck, scope: e.target.value })}
                placeholder="Scope (optional)" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={handleCheckQuota} style={btnPrimary}>Check</button>
            </div>
          </div>

          {/* Quota result */}
          {quotaResult && (
            <div style={{ padding: '12px', background: colors.bg, borderRadius: '8px', border: `1px solid ${colors.border}` }}>
              <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600, color: colors.green }}>Quota Result</h4>
              <pre style={{ fontSize: '12px', color: colors.text, whiteSpace: 'pre-wrap', margin: 0, overflow: 'auto', maxHeight: '200px' }}>
                {JSON.stringify(quotaResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Schedule Tab */}
      {activeTab === 'Schedule' && (
        <div className="dashboard-section" style={{ background: colors.card, border: `1px solid ${colors.border}`, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Schedule</h3>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <button onClick={handleGetSchedule} disabled={scheduleLoading} style={btnPrimary}>
              {scheduleLoading ? 'Loading...' : 'Get Schedule'}
            </button>
            <button onClick={handleOptimizeSchedule} disabled={scheduleLoading} style={{ ...btnSecondary, borderColor: colors.green, color: colors.green }}>
              {scheduleLoading ? 'Optimizing...' : 'Optimize Schedule'}
            </button>
          </div>
          {schedule ? (
            <div>
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>Schedule Summary</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '8px' }}>
                  {[
                    { label: 'Total Tasks', value: schedule.total_tasks ?? schedule.total ?? 'N/A' },
                    { label: 'Scheduled', value: schedule.scheduled ?? schedule.scheduled_count ?? 'N/A' },
                    { label: 'Estimated Time', value: schedule.estimated_time ?? schedule.eta ?? 'N/A' },
                    { label: 'Efficiency', value: schedule.efficiency ? (schedule.efficiency * 100).toFixed(1) + '%' : 'N/A' },
                  ].map((item) => (
                    <div key={item.label} style={{ background: colors.bg, borderRadius: '8px', padding: '10px', textAlign: 'center', border: `1px solid ${colors.border}` }}>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: colors.accent }}>{item.value}</div>
                      <div style={{ fontSize: '11px', color: colors.textSecondary, marginTop: '4px' }}>{item.label}</div>
                    </div>
                  ))}
                </div>
              </div>
              {schedule.entries && (
                <div>
                  <h4 style={{ margin: '0 0 8px', fontSize: '14px', fontWeight: 600 }}>Schedule Entries</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {schedule.entries.map((entry: any, idx: number) => (
                      <div key={entry.task_id || idx} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '10px 14px', background: colors.bg, borderRadius: '8px',
                        border: `1px solid ${colors.border}`, fontSize: '13px',
                      }}>
                        <span style={{ fontWeight: 600 }}>{entry.task_id || `Task ${idx + 1}`}</span>
                        <span style={{ color: colors.textSecondary }}>
                          {entry.start_time ? `Start: ${entry.start_time}` : ''}
                          {entry.priority ? ` | Priority: ${entry.priority}` : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <pre style={{ fontSize: '12px', color: colors.text, whiteSpace: 'pre-wrap', margin: '16px 0 0', overflow: 'auto', maxHeight: '300px', background: colors.bg, padding: '12px', borderRadius: '8px', border: `1px solid ${colors.border}` }}>
                {JSON.stringify(schedule, null, 2)}
              </pre>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '40px 0', color: colors.textSecondary }}>
              {scheduleLoading ? 'Loading schedule...' : 'Click "Get Schedule" to view the current schedule'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};