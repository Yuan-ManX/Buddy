import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { WorkflowTaskItem, WorkflowStats, WorkflowBlocker } from '../types';

const STATE_COLORS: Record<string, string> = {
  backlog: '#9ca3af',
  todo: '#6b7280',
  in_progress: '#3b82f6',
  blocked: '#ef4444',
  done: '#10b981',
  cancelled: '#9ca3af',
};

const PRIORITY_EMOJIS: Record<string, string> = {
  low: '🔵',
  medium: '🟡',
  high: '🟠',
  urgent: '🔴',
};

const STATE_NAMES: Record<string, string> = {
  backlog: 'Backlog',
  todo: 'To Do',
  in_progress: 'In Progress',
  blocked: 'Blocked',
  done: 'Done',
  cancelled: 'Cancelled',
};

export const WorkflowPanel: React.FC = () => {
  const [tasks, setTasks] = useState<WorkflowTaskItem[]>([]);
  const [stats, setStats] = useState<WorkflowStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [showBlockers, setShowBlockers] = useState(false);
  const [blockers, setBlockers] = useState<WorkflowBlocker[]>([]);
  const [stateFilter, setStateFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');

  const [newTask, setNewTask] = useState({
    title: '', description: '', priority: 'medium' as const,
    assigned_agent: '', studio_id: '', dependencies: [] as string[],
  });
  const [newBlocker, setNewBlocker] = useState({ blocker_type: 'technical', description: '' });

  useEffect(() => { loadData(); }, [stateFilter, priorityFilter]);

  const loadData = async () => {
    try {
      const [taskRes, statsRes] = await Promise.all([
        api.workflows.list(stateFilter || undefined, priorityFilter || undefined),
        api.workflows.stats(),
      ]);
      setTasks(taskRes.tasks);
      setStats(statsRes);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load workflow tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newTask.title.trim()) return;
    try {
      await api.workflows.create(newTask);
      setShowCreate(false);
      setNewTask({ title: '', description: '', priority: 'medium', assigned_agent: '', studio_id: '', dependencies: [] });
      loadData();
    } catch (e: any) { setError(e.message); }
  };

  const handleTransition = async (task: WorkflowTaskItem, newState: string) => {
    try { await api.workflows.transition(task.id, newState); loadData(); } catch (e: any) { setError(e.message); }
  };

  const handleAssign = async (task: WorkflowTaskItem, agentId: string) => {
    if (!agentId.trim()) return;
    try { await api.workflows.assign(task.id, agentId.trim()); loadData(); } catch (e: any) { setError(e.message); }
  };

  const handleReportBlocker = async (taskId: string) => {
    if (!selectedTask) return;
    if (!newBlocker.description.trim()) return;
    try {
      await api.workflows.blockers.create(taskId, newBlocker.blocker_type, newBlocker.description);
      loadBlockers(taskId);
      setNewBlocker({ blocker_type: 'technical', description: '' });
      loadData();
    } catch (e: any) { setError(e.message); }
  };

  const handleResolveBlocker = async (taskId: string, blockerId: string) => {
    try {
      await api.workflows.blockers.resolve(taskId, blockerId);
      loadBlockers(taskId);
      loadData();
    } catch (e: any) { setError(e.message); }
  };

  const loadBlockers = async (taskId: string) => {
    try {
      const res = await api.workflows.blockers.list(taskId);
      setBlockers(res.blockers);
    } catch (e: any) { setError(e.message); }
  };

  const getStateColor = (state: string) => STATE_COLORS[state] || '#6b7280';
  const getPriorityEmoji = (p: string) => PRIORITY_EMOJIS[p] || '⚪';
  const formatTime = (iso: string) => iso ? new Date(iso).toLocaleString() : 'N/A';

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header"><h2>Workflow Manager</h2><p className="panel-subtitle">Agentic Task Lifecycle & Collaboration</p></div>
        <div className="panel-loading"><div className="spinner" /><span>Loading tasks...</span></div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Workflow Manager</h2>
        <p className="panel-subtitle">Agentic Task Lifecycle & Collaboration</p>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-icon">📋</span>
            <div className="stat-content"><span className="stat-value">{stats.total_tasks}</span><span className="stat-label">Total Tasks</span></div>
          </div>
          {Object.entries(stats.tasks_by_state || {}).slice(0, 4).map(([state, count]) => (
            <div key={state} className="stat-item">
              <span className="stat-icon" style={{ color: getStateColor(state) }}>●</span>
              <div className="stat-content"><span className="stat-value">{String(count)}</span><span className="stat-label">{STATE_NAMES[state] || state}</span></div>
            </div>
          ))}
          {stats.unresolved_blockers > 0 && (
            <div className="stat-item">
              <span className="stat-icon">⚠️</span>
              <div className="stat-content"><span className="stat-value" style={{ color: '#ef4444' }}>{stats.unresolved_blockers}</span><span className="stat-label">Open Blockers</span></div>
            </div>
          )}
        </div>
      )}

      {/* Filters & Actions */}
      <div className="action-bar">
        <button className="btn-primary-sm" onClick={() => setShowCreate(true)}>+ New Task</button>
        <select value={stateFilter} onChange={e => setStateFilter(e.target.value)}>
          <option value="">All States</option>
          <option value="todo">To Do</option>
          <option value="backlog">Backlog</option>
          <option value="in_progress">In Progress</option>
          <option value="blocked">Blocked</option>
          <option value="done">Done</option>
        </select>
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}>
          <option value="">All Priorities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <button className="btn-secondary-sm" onClick={loadData}>🔄 Refresh</button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create Task</h3>
            <div className="form-group">
              <label>Title</label>
              <input type="text" value={newTask.title} onChange={e => setNewTask({ ...newTask, title: e.target.value })} placeholder="Task title" autoFocus />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea rows={3} value={newTask.description} onChange={e => setNewTask({ ...newTask, description: e.target.value })} placeholder="Describe what needs to be done..." />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Priority</label>
                <select value={newTask.priority} onChange={e => setNewTask({ ...newTask, priority: e.target.value } as any)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
              <div className="form-group">
                <label>Assigned Agent (ID)</label>
                <input type="text" value={newTask.assigned_agent} onChange={e => setNewTask({ ...newTask, assigned_agent: e.target.value })} placeholder="agent-..." />
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Task Kanban */}
      <div className="kanban-board">
        {['backlog', 'todo', 'in_progress', 'blocked', 'done'].map(state => {
          const columnTasks = tasks.filter(t => t.state === state);
          return (
            <div key={state} className="kanban-column">
              <div className="kanban-header">
                <span className="kanban-title" style={{ color: getStateColor(state) }}>
                  {STATE_NAMES[state]} ({columnTasks.length})
                </span>
              </div>
              <div className="kanban-cards">
                {columnTasks.map(task => (
                  <div key={task.id} className="kanban-card">
                    <div className="task-header">
                      <span className="task-priority">{getPriorityEmoji(task.priority)} {task.priority}</span>
                      <span className="task-state" style={{ color: getStateColor(task.state) }}>● {task.state}</span>
                    </div>
                    <h4 className="task-title">{task.title}</h4>
                    {task.description && <p className="task-description">{task.description}</p>}
                    <div className="task-meta">
                      {task.assigned_agent && <span className="task-meta-item">👤 {task.assigned_agent.slice(0, 8)}...</span>}
                      {task.active_blockers > 0 && <span className="task-meta-item blocker">⚠️ {task.active_blockers} blocker(s)</span>}
                      <span className="task-meta-item">📅 {formatTime(task.created_at)}</span>
                    </div>
                    <div className="task-actions">
                      {task.state !== 'todo' && <button className="btn-mini" onClick={() => handleTransition(task, 'todo')}>↶ To Do</button>}
                      {task.state !== 'in_progress' && <button className="btn-mini" onClick={() => handleTransition(task, 'in_progress')}>▶ Start</button>}
                      {task.state !== 'done' && <button className="btn-mini" onClick={() => handleTransition(task, 'done')}>✅ Done</button>}
                      <button className="btn-mini" onClick={() => { setSelectedTask(task.id); setShowBlockers(true); loadBlockers(task.id); }}>
                        🚧 {task.active_blockers > 0 ? `(${task.active_blockers})` : 'Blockers'}
                      </button>
                    </div>
                  </div>
                ))}
                {columnTasks.length === 0 && <div className="empty-column">No tasks</div>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Blocker Modal */}
      {showBlockers && selectedTask && (
        <div className="modal-overlay" onClick={() => { setShowBlockers(false); setSelectedTask(null); }}>
          <div className="modal large" onClick={e => e.stopPropagation()}>
            <h3>Task Blockers</h3>
            <div className="form-group">
              <label>New Blocker</label>
              <div className="form-row">
                <select value={newBlocker.blocker_type} onChange={e => setNewBlocker({ ...newBlocker, blocker_type: e.target.value })}>
                  <option value="technical">Technical</option>
                  <option value="dependency">Dependency</option>
                  <option value="approval">Approval</option>
                  <option value="external">External</option>
                </select>
              </div>
              <textarea
                rows={2}
                value={newBlocker.description}
                onChange={e => setNewBlocker({ ...newBlocker, description: e.target.value })}
                placeholder="Describe the blocker..."
              />
              <button className="btn-primary-sm" style={{ marginTop: 8 }} onClick={() => handleReportBlocker(selectedTask)}>
                + Report Blocker
              </button>
            </div>
            <div className="blocker-list">
              <h4 className="section-label">Open Blockers</h4>
              {blockers.filter(b => !b.resolved).map(b => (
                <div key={b.id} className="blocker-item">
                  <div>
                    <strong>{b.blocker_type}</strong>: {b.description}
                    <div className="blocker-meta">reported {formatTime(b.created_at)}</div>
                  </div>
                  <button className="btn-mini" onClick={() => handleResolveBlocker(selectedTask, b.id)}>✅ Resolve</button>
                </div>
              ))}
              {blockers.filter(b => !b.resolved).length === 0 && <div className="empty-column">No open blockers</div>}
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => { setShowBlockers(false); setSelectedTask(null); }}>Close</button>
            </div>
          </div>
        </div>
      )}

      <style>{styles}</style>
    </div>
  );
};

const styles = `
.panel-container { padding: 24px; max-width: 1400px; margin: 0 auto; }
.panel-header h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; color: var(--text, #1f2937); }
.panel-subtitle { color: var(--text-secondary, #6b7280); margin-bottom: 24px; font-size: 0.9rem; }
.panel-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 0; color: var(--text-secondary, #9ca3af); gap: 16px; font-size: 0.95rem; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--border, #e5e7eb); border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-banner { background: #fef2f2; color: #991b1b; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; }

.stats-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-item { flex: 1; min-width: 140px; background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 14px 18px; display: flex; align-items: center; gap: 12px; }
.stat-icon { font-size: 1.5rem; }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: 1.3rem; font-weight: 800; color: var(--text, #1f2937); }
.stat-label { font-size: 0.72rem; color: var(--text-secondary, #6b7280); font-weight: 600; }

.action-bar { display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; align-items: center; }
.action-bar select { padding: 8px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.85rem; background: var(--bg-card, #fff); color: var(--text, #374151); }
.btn-primary-sm { padding: 8px 16px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-primary-sm:hover { background: #2563eb; }
.btn-secondary-sm { padding: 8px 16px; background: var(--bg-card, #fff); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-secondary-sm:hover { border-color: #3b82f6; color: #3b82f6; }
.btn-danger-sm { padding: 6px 12px; background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.8rem; }
.btn-danger-sm:hover { background: #fee2e2; }

.kanban-board { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; overflow-x: auto; }
.kanban-column { background: var(--bg-card, #f9fafb); border-radius: 12px; padding: 12px; min-height: 400px; }
.kanban-header { padding-bottom: 8px; margin-bottom: 12px; border-bottom: 2px solid var(--border, #e5e7eb); }
.kanban-title { font-weight: 700; font-size: 0.9rem; }
.kanban-cards { display: flex; flex-direction: column; gap: 10px; }
.kanban-card { background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 10px; padding: 14px; transition: box-shadow 0.15s; }
.kanban-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.task-priority { font-size: 0.75rem; font-weight: 600; color: var(--text-secondary, #6b7280); text-transform: capitalize; }
.task-state { font-size: 0.75rem; font-weight: 700; text-transform: lowercase; }
.task-title { font-size: 0.95rem; font-weight: 700; color: var(--text, #1f2937); margin-bottom: 6px; }
.task-description { font-size: 0.82rem; color: var(--text-secondary, #4b5563); margin-bottom: 10px; line-height: 1.4; }
.task-meta { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.task-meta-item { font-size: 0.75rem; color: var(--text-secondary, #6b7280); }
.task-meta-item.blocker { color: #ef4444; font-weight: 600; }
.task-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.btn-mini { padding: 4px 8px; background: var(--bg-card, #f3f4f6); border: 1px solid var(--border, #d1d5db); border-radius: 6px; font-size: 0.7rem; cursor: pointer; color: var(--text, #374151); }
.btn-mini:hover { border-color: #3b82f6; color: #3b82f6; }
.empty-column { text-align: center; padding: 24px 8px; color: var(--text-secondary, #9ca3af); font-size: 0.85rem; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text, #374151); }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.9rem; background: var(--bg-card, #fff); color: var(--text, #1f2937); font-family: inherit; }
.form-group textarea { resize: vertical; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }

.blocker-list { margin-top: 16px; max-height: 300px; overflow-y: auto; }
.blocker-item { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 12px; background: var(--bg-card, #fef2f2); border: 1px solid var(--border, #fecaca); border-radius: 8px; margin-bottom: 8px; }
.blocker-meta { font-size: 0.75rem; color: var(--text-secondary, #6b7280); margin-top: 4px; }
.section-label { font-size: 0.85rem; font-weight: 700; color: var(--text-secondary, #6b7280); margin-bottom: 10px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--bg-card, #fff); border-radius: 16px; padding: 28px; width: 90%; max-width: 480px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal.large { max-width: 640px; }
.modal h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 20px; color: var(--text, #1f2937); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.btn-primary { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { padding: 10px 20px; background: var(--bg-card, #f3f4f6); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
`;

export default WorkflowPanel;