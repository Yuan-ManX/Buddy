import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

interface ProactiveTask {
  id: string;
  title: string;
  description: string;
  source: string;
  urgency: string;
  related_memory_ids: string[];
  suggested_agent_role: string;
  suggested_action: string;
  confidence: number;
  auto_schedulable: boolean;
  estimated_effort: string;
  created_at: string;
  status: string;
}

interface DiscoveryStats {
  agent_id: string;
  is_running: boolean;
  scan_interval: number;
  total_scans: number;
  total_discoveries: number;
  last_scan_at: string;
  tasks_by_status: Record<string, number>;
  tasks_by_source: Record<string, number>;
  total_insights: number;
}

const URGENCY_EMOJIS: Record<string, string> = {
  now: '🔴',
  soon: '🟡',
  later: '🟢',
  someday: '⚪',
};

const URGENCY_LEVELS: Record<string, string> = {
  now: 'Now',
  soon: 'Soon',
  later: 'Later',
  someday: 'Someday',
};

const SOURCE_LABELS: Record<string, string> = {
  memory_pattern: 'Memory Pattern',
  conversation_gap: 'Conversation Gap',
  behavioral_signal: 'Behavioral Signal',
  system_optimization: 'System Optimization',
  external_event: 'External Event',
  scheduled_scan: 'Scheduled Scan',
};

interface ProactiveDiscoveryPanelProps {
  agent: { id: string; name: string };
}

export const ProactiveDiscoveryPanel: React.FC<ProactiveDiscoveryPanelProps> = ({ agent }) => {
  const [stats, setStats] = useState<DiscoveryStats | null>(null);
  const [tasks, setTasks] = useState<ProactiveTask[]>([]);
  const [insights, setInsights] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [scanning, setScanning] = useState(false);
  const [activeTab, setActiveTab] = useState<'tasks' | 'insights' | 'stats'>('tasks');
  const { success: showSuccess, error: showError } = useToast();

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, tasksRes, insightsRes] = await Promise.all([
        api.proactive.status(agent.id),
        api.proactive.tasks(agent.id, { status: statusFilter || undefined, limit: 100 }),
        api.proactive.insights(agent.id, 20),
      ]);
      setStats(statsRes as unknown as DiscoveryStats);
      setTasks(tasksRes.tasks as unknown as ProactiveTask[]);
      setInsights(insightsRes.insights);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load proactive discovery data');
    } finally {
      setLoading(false);
    }
  }, [agent.id, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleScan = async () => {
    try {
      setScanning(true);
      const result = await api.proactive.scan(agent.id);
      showSuccess(`Discovered ${result.tasks_discovered || 0} tasks`);
      loadData();
    } catch (e: any) {
      showError('Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleStart = async () => {
    try {
      await api.proactive.start(agent.id, 600);
      showSuccess('Always-On discovery started');
      loadData();
    } catch (e: any) {
      showError('Failed to start');
    }
  };

  const handleStop = async () => {
    try {
      await api.proactive.stop(agent.id);
      showSuccess('Discovery stopped');
      loadData();
    } catch (e: any) {
      showError('Failed to stop');
    }
  };

  const handleSchedule = async (taskId: string) => {
    try {
      await api.proactive.scheduleTask(agent.id, taskId);
      showSuccess('Task scheduled');
      loadData();
    } catch (e: any) {
      showError('Failed to schedule');
    }
  };

  const handleDismiss = async (taskId: string) => {
    try {
      await api.proactive.dismissTask(agent.id, taskId);
      showSuccess('Task dismissed');
      loadData();
    } catch (e: any) {
      showError('Failed to dismiss');
    }
  };

  const handleComplete = async (taskId: string) => {
    try {
      await api.proactive.completeTask(agent.id, taskId);
      showSuccess('Task completed');
      loadData();
    } catch (e: any) {
      showError('Failed to complete');
    }
  };

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  if (loading && !tasks.length) {
    return <div className="panel-loading">Loading proactive discovery...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Proactive Discovery</h2>
        <div className="panel-header-actions">
          {stats?.is_running ? (
            <button className="btn-secondary" onClick={handleStop}>
              ⏹ Stop
            </button>
          ) : (
            <button className="btn-secondary" onClick={handleStart}>
              ▶ Always-On
            </button>
          )}
          <button className="btn-primary" onClick={handleScan} disabled={scanning}>
            {scanning ? '⏳ Scanning...' : '🔍 Scan Now'}
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {/* Stats bar */}
      {stats && (
        <div className="board-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_discoveries}</span>
            <span className="stat-label">Total Discoveries</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_scans}</span>
            <span className="stat-label">Scans</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_insights}</span>
            <span className="stat-label">Insights</span>
          </div>
          <div className="stat-card">
            <span className={`stat-value ${stats.is_running ? 'text-green' : ''}`}>
              {stats.is_running ? 'Active' : 'Idle'}
            </span>
            <span className="stat-label">Status</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{formatDate(stats.last_scan_at)}</span>
            <span className="stat-label">Last Scan</span>
          </div>
        </div>
      )}

      {/* Tab switcher */}
      <div className="tabs-row">
        <button
          className={`tab-btn ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          Tasks ({tasks.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveTab('insights')}
        >
          Insights ({insights.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          Statistics
        </button>
      </div>

      {/* Tasks tab */}
      {activeTab === 'tasks' && (
        <>
          <div className="filters-row">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="scheduled">Scheduled</option>
              <option value="completed">Completed</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>

          {tasks.length === 0 ? (
            <div className="panel-empty">
              <p>No proactive tasks discovered yet.</p>
              <p className="hint">Run a scan to discover tasks based on agent memory and context.</p>
            </div>
          ) : (
            <div className="task-list">
              {tasks.map((task) => (
                <div key={task.id} className={`task-card ${task.status}`}>
                  <div className="task-card-header">
                    <span className="task-urgency">
                      {URGENCY_EMOJIS[task.urgency] || '⚪'} {URGENCY_LEVELS[task.urgency] || task.urgency}
                    </span>
                    <span className="task-confidence">
                      {Math.round(task.confidence * 100)}% confidence
                    </span>
                    <span className="task-source">
                      {SOURCE_LABELS[task.source] || task.source}
                    </span>
                  </div>
                  <div className="task-card-body">
                    <h4>{task.title}</h4>
                    <p>{task.description}</p>
                    <div className="task-meta">
                      {task.auto_schedulable && (
                        <span className="badge badge-auto">Auto-Schedulable</span>
                      )}
                      <span className="badge badge-effort">{task.estimated_effort}</span>
                      <span className="badge">{task.status}</span>
                    </div>
                  </div>
                  {task.status === 'pending' && (
                    <div className="task-card-actions">
                      <button
                        className="btn-sm btn-primary"
                        onClick={() => handleSchedule(task.id)}
                      >
                        Schedule
                      </button>
                      <button
                        className="btn-sm btn-secondary"
                        onClick={() => handleDismiss(task.id)}
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                  {task.status === 'scheduled' && (
                    <div className="task-card-actions">
                      <button
                        className="btn-sm btn-primary"
                        onClick={() => handleComplete(task.id)}
                      >
                        Complete
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Insights tab */}
      {activeTab === 'insights' && (
        <>
          {insights.length === 0 ? (
            <div className="panel-empty">
              <p>No insights generated yet.</p>
              <p className="hint">Insights are generated during proactive scans as patterns are detected.</p>
            </div>
          ) : (
            <div className="insight-list">
              {insights.map((insight, i) => (
                <div key={i} className="insight-item">
                  <span className="insight-bullet">💡</span>
                  <span>{insight}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Stats tab */}
      {activeTab === 'stats' && stats && (
        <div className="stats-detail">
          <div className="stats-section">
            <h3>Task Status Distribution</h3>
            <div className="stats-grid">
              {Object.entries(stats.tasks_by_status).map(([status, count]) => (
                <div key={status} className="stat-item">
                  <span className="stat-label">{status}</span>
                  <span className="stat-value">{count}</span>
                </div>
              ))}
              {Object.keys(stats.tasks_by_status).length === 0 && (
                <p className="hint">No tasks yet</p>
              )}
            </div>
          </div>

          <div className="stats-section">
            <h3>Task Source Distribution</h3>
            <div className="stats-grid">
              {Object.entries(stats.tasks_by_source).map(([source, count]) => (
                <div key={source} className="stat-item">
                  <span className="stat-label">{SOURCE_LABELS[source] || source}</span>
                  <span className="stat-value">{count}</span>
                </div>
              ))}
              {Object.keys(stats.tasks_by_source).length === 0 && (
                <p className="hint">No tasks yet</p>
              )}
            </div>
          </div>

          <div className="stats-section">
            <h3>Engine Info</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-label">Agent ID</span>
                <span className="stat-value">{stats.agent_id}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Scan Interval</span>
                <span className="stat-value">{stats.scan_interval}s</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Total Scans</span>
                <span className="stat-value">{stats.total_scans}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Total Discoveries</span>
                <span className="stat-value">{stats.total_discoveries}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};