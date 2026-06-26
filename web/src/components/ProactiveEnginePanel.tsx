import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Local type definitions for proactive engine data shapes
interface ProactiveStats {
  running: boolean;
  total_discovered: number;
  total_completed: number;
  queue_size: number;
  monitors: number;
  is_idle: boolean;
}

interface ProactiveTask {
  task_id: string;
  description: string;
  priority: number;
  source: string;
  status: string;
  created_at: string;
}

interface ProactiveCompletedTask {
  task_id: string;
  description: string;
  source: string;
  completed_at: string;
  result?: string;
}

interface ProactiveMonitor {
  monitor_id: string;
  name: string;
  source: string;
  check_interval_seconds: number;
  enabled: boolean;
  last_check_at?: string;
}

export const ProactiveEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<ProactiveStats | null>(null);
  const [queue, setQueue] = useState<ProactiveTask[]>([]);
  const [completed, setCompleted] = useState<ProactiveCompletedTask[]>([]);
  const [monitors, setMonitors] = useState<ProactiveMonitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'queue' | 'completed' | 'monitors' | 'controls'>('overview');
  const [priorityInputs, setPriorityInputs] = useState<Record<string, number>>({});

  // Load all data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, q, c, m] = await Promise.all([
        api.proactiveEngine.stats(),
        api.proactiveEngine.queue(),
        api.proactiveEngine.completed(),
        api.proactiveEngine.monitors(),
      ]);
      setStats(s);
      setQueue(q.tasks || q.queue || []);
      setCompleted(c.tasks || c.completed || []);
      setMonitors(m.monitors || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load proactive engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Actions ──

  const handleDiscover = async () => {
    try {
      const result = await api.proactiveEngine.discover();
      toast.success(`Discovered: ${result.discovered ?? result.message ?? 'tasks discovered'}`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleExecute = async () => {
    try {
      const result = await api.proactiveEngine.execute();
      toast.success(result.message || 'Task executed');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleSkip = async (taskId: string) => {
    try {
      await api.proactiveEngine.skip(taskId);
      toast.success(`Task ${taskId} skipped`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handlePrioritize = async (taskId: string) => {
    const priority = priorityInputs[taskId];
    if (priority === undefined || priority === null) return;
    try {
      await api.proactiveEngine.prioritize(taskId, priority);
      toast.success(`Priority updated for ${taskId}`);
      setPriorityInputs((prev) => {
        const next = { ...prev };
        delete next[taskId];
        return next;
      });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleClearCompleted = async () => {
    try {
      await api.proactiveEngine.clearCompleted();
      toast.success('Completed tasks cleared');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleToggleMonitor = async (monitorId: string, enabled: boolean) => {
    try {
      await api.proactiveEngine.toggleMonitor(monitorId, enabled);
      toast.success(`Monitor ${enabled ? 'enabled' : 'disabled'}`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleStart = async () => {
    try {
      await api.proactiveEngine.start();
      toast.success('Engine started');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleStop = async () => {
    try {
      await api.proactiveEngine.stop();
      toast.success('Engine stopped');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // ── Priority color helpers ──

  const priorityColor = (p: number): string => {
    if (p >= 8) return '#ef4444';
    if (p >= 5) return '#f59e0b';
    if (p >= 3) return '#3b82f6';
    return '#9ca3af';
  };

  const priorityLabel = (p: number): string => {
    if (p >= 8) return 'Critical';
    if (p >= 5) return 'High';
    if (p >= 3) return 'Medium';
    return 'Low';
  };

  // ── Loading state ──

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Proactive Engine</h2>
          <p className="panel-subtitle">Autonomous task discovery and execution engine</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading proactive engine data...</span>
        </div>
      </div>
    );
  }

  // ── Render ──

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Proactive Engine</h2>
        <p className="panel-subtitle">Autonomous task discovery, prioritization, and execution engine</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stats.running ? '#22c55e' : '#9ca3af' }}>
                {stats.running ? 'Running' : 'Stopped'}
              </span>
              <span className="stat-label">Status</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_discovered}</span>
              <span className="stat-label">Total Discovered</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.total_completed}</span>
              <span className="stat-label">Completed</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.queue_size}</span>
              <span className="stat-label">Queue Size</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.monitors}</span>
              <span className="stat-label">Monitors</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: stats.is_idle ? '#f59e0b' : '#22c55e' }}>
                {stats.is_idle ? 'Idle' : 'Active'}
              </span>
              <span className="stat-label">Idle Status</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'queue', 'completed', 'monitors', 'controls'] as const).map((s) => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Engine Overview</h3>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
            <div style={{ flex: '1 0 200px', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>Status</h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    background: stats.running ? '#22c55e' : '#9ca3af',
                    display: 'inline-block',
                  }}
                />
                <strong>{stats.running ? 'Running' : 'Stopped'}</strong>
              </div>
            </div>
            <div style={{ flex: '1 0 200px', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>Idle Status</h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    background: stats.is_idle ? '#f59e0b' : '#22c55e',
                    display: 'inline-block',
                  }}
                />
                <strong>{stats.is_idle ? 'Idle' : 'Active'}</strong>
              </div>
            </div>
            <div style={{ flex: '1 0 200px', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>Queue</h4>
              <strong style={{ fontSize: '1.5rem', color: '#3b82f6' }}>{stats.queue_size}</strong>
              <span style={{ marginLeft: 8, color: '#6b7280' }}>pending tasks</span>
            </div>
          </div>

          <h3>Progress Summary</h3>
          <div className="dashboard-stat-row">
            <span>Total Discovered</span>
            <strong>{stats.total_discovered}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Total Completed</span>
            <strong style={{ color: '#22c55e' }}>{stats.total_completed}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Completion Rate</span>
            <strong>
              {stats.total_discovered > 0
                ? ((stats.total_completed / stats.total_discovered) * 100).toFixed(1) + '%'
                : 'N/A'}
            </strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Active Monitors</span>
            <strong>{stats.monitors}</strong>
          </div>
        </div>
      )}

      {/* Queue */}
      {activeSection === 'queue' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3>Task Queue ({queue.length})</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn-sm"
                style={{ background: '#4f6ef7', color: '#fff', border: 'none' }}
                onClick={handleDiscover}
              >
                Discover Tasks
              </button>
              <button
                className="btn-sm"
                style={{ background: '#22c55e', color: '#fff', border: 'none' }}
                onClick={handleExecute}
              >
                Execute Next
              </button>
            </div>
          </div>

          {queue.length === 0 ? (
            <div className="panel-empty">No tasks in queue. Click "Discover Tasks" to find new tasks.</div>
          ) : (
            <div className="forge-skill-list">
              {queue.map((task) => (
                <div key={task.task_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{task.description}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: priorityColor(task.priority),
                        color: '#fff',
                      }}
                    >
                      {priorityLabel(task.priority)} ({task.priority})
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Source: {task.source || 'unknown'} | Status: {task.status}</div>
                    <div>Created: {new Date(task.created_at).toLocaleString()}</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <button
                      className="btn-sm"
                      style={{ background: '#ef4444', color: '#fff', border: 'none' }}
                      onClick={() => handleSkip(task.task_id)}
                    >
                      Skip
                    </button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        placeholder="Priority"
                        value={priorityInputs[task.task_id] ?? ''}
                        onChange={(e) =>
                          setPriorityInputs((prev) => ({
                            ...prev,
                            [task.task_id]: parseInt(e.target.value) || 0,
                          }))
                        }
                        style={{
                          width: 80,
                          padding: '4px 8px',
                          borderRadius: 4,
                          border: '1px solid #d1d5db',
                          fontSize: '0.85rem',
                        }}
                      />
                      <button
                        className="btn-sm"
                        style={{ background: '#f59e0b', color: '#fff', border: 'none' }}
                        onClick={() => handlePrioritize(task.task_id)}
                      >
                        Set Priority
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Completed */}
      {activeSection === 'completed' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3>Completed Tasks ({completed.length})</h3>
            <button
              className="btn-sm"
              style={{ background: '#ef4444', color: '#fff', border: 'none' }}
              onClick={handleClearCompleted}
            >
              Clear All
            </button>
          </div>

          {completed.length === 0 ? (
            <div className="panel-empty">No completed tasks yet.</div>
          ) : (
            <div className="forge-skill-list">
              {completed.map((task) => (
                <div key={task.task_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{task.description}</div>
                    <span
                      className="dashboard-badge"
                      style={{ background: '#22c55e', color: '#fff' }}
                    >
                      Completed
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Source: {task.source || 'unknown'}</div>
                    <div>Completed: {new Date(task.completed_at).toLocaleString()}</div>
                    {task.result && (
                      <div style={{ marginTop: 4, color: '#6b7280', fontSize: '0.85rem' }}>
                        Result: {task.result}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Monitors */}
      {activeSection === 'monitors' && (
        <div className="dashboard-section">
          <h3>Monitors ({monitors.length})</h3>

          {monitors.length === 0 ? (
            <div className="panel-empty">No monitors configured.</div>
          ) : (
            <div className="forge-skill-list">
              {monitors.map((monitor) => (
                <div key={monitor.monitor_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{monitor.name}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: monitor.enabled ? '#22c55e' : '#9ca3af',
                        color: '#fff',
                      }}
                    >
                      {monitor.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Source: {monitor.source || 'none'} | Interval: {monitor.check_interval_seconds}s</div>
                    {monitor.last_check_at && (
                      <div>Last Check: {new Date(monitor.last_check_at).toLocaleString()}</div>
                    )}
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <button
                      className="btn-sm"
                      style={{
                        background: monitor.enabled ? '#ef4444' : '#22c55e',
                        color: '#fff',
                        border: 'none',
                      }}
                      onClick={() => handleToggleMonitor(monitor.monitor_id, !monitor.enabled)}
                    >
                      {monitor.enabled ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Controls */}
      {activeSection === 'controls' && (
        <div className="dashboard-section">
          <h3>Engine Controls</h3>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
            <button
              className="btn-primary"
              style={{ background: '#22c55e', color: '#fff', border: 'none' }}
              onClick={handleStart}
            >
              Start Engine
            </button>
            <button
              className="btn-primary"
              style={{ background: '#ef4444', color: '#fff', border: 'none' }}
              onClick={handleStop}
            >
              Stop Engine
            </button>
          </div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
            <button
              className="btn-primary"
              style={{ background: '#4f6ef7', color: '#fff', border: 'none' }}
              onClick={handleDiscover}
            >
              Run Task Discovery
            </button>
            <button
              className="btn-primary"
              style={{ background: '#8b5cf6', color: '#fff', border: 'none' }}
              onClick={handleExecute}
            >
              Execute Next Task
            </button>
          </div>

          {stats && (
            <div style={{ padding: 16, background: '#f8fafc', borderRadius: 8 }}>
              <h4 style={{ margin: '0 0 12px 0', color: '#374151' }}>Current Status</h4>
              <div className="dashboard-stat-row">
                <span>Engine Running</span>
                <strong style={{ color: stats.running ? '#22c55e' : '#ef4444' }}>
                  {stats.running ? 'Yes' : 'No'}
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Idle</span>
                <strong style={{ color: stats.is_idle ? '#f59e0b' : '#22c55e' }}>
                  {stats.is_idle ? 'Yes' : 'No'}
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Queue Size</span>
                <strong>{stats.queue_size}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Completed</span>
                <strong>{stats.total_completed}</strong>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProactiveEnginePanel;