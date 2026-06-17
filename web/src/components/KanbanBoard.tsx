import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface BoardTask {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  assignee: string;
  labels: string[];
  created_at: string;
  updated_at: string;
  due_date: string;
  blocked_by: string[];
}

interface Column {
  id: string;
  title: string;
  status: string;
  color: string;
}

const DEFAULT_COLUMNS: Column[] = [
  { id: 'backlog', title: 'Backlog', status: 'backlog', color: '#6b7280' },
  { id: 'todo', title: 'To Do', status: 'todo', color: '#3b82f6' },
  { id: 'in_progress', title: 'In Progress', status: 'in_progress', color: '#f59e0b' },
  { id: 'review', title: 'Review', status: 'review', color: '#8b5cf6' },
  { id: 'done', title: 'Done', status: 'done', color: '#10b981' },
];

export const KanbanBoard: React.FC = () => {
  const [tasks, setTasks] = useState<BoardTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dragTask, setDragTask] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTask, setNewTask] = useState({ title: '', description: '', priority: 'medium', labels: '' });
  const [filter, setFilter] = useState({ priority: '', assignee: '' });

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.tasks.list({ page_size: 100 });
      const tasks = (data.items || []).map((t: any) => ({
        id: t.id,
        title: t.title || t.name || '',
        description: t.description || '',
        status: t.status || 'backlog',
        priority: t.priority || 'medium',
        assignee: t.assignee || t.agent_id || '',
        labels: t.labels || t.tags || [],
        created_at: t.created_at || '',
        updated_at: t.updated_at || '',
        due_date: t.due_date || '',
        blocked_by: t.blocked_by || t.depends_on || [],
      }));
      setTasks(tasks);
    } catch (e) {
      // Fallback: use empty board if tasks API unavailable
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleDragStart = (taskId: string) => {
    setDragTask(taskId);
  };

  const handleDrop = async (status: string) => {
    if (!dragTask) return;
    setTasks(prev =>
      prev.map(t => (t.id === dragTask ? { ...t, status, updated_at: new Date().toISOString() } : t))
    );
    setDragTask(null);

    try {
      await api.tasks.transition(dragTask, status);
    } catch {
      loadTasks(); // Revert on failure
    }
  };

  const handleCreateTask = async () => {
    if (!newTask.title.trim()) return;
    try {
      await api.tasks.create({
        agent_id: '',
        title: newTask.title,
        kind: 'kanban',
        payload: {
          description: newTask.description,
          priority: newTask.priority,
          labels: newTask.labels.split(',').map((l: string) => l.trim()).filter(Boolean),
          status: 'backlog',
        },
        max_attempts: 1,
      });
      setNewTask({ title: '', description: '', priority: 'medium', labels: '' });
      setShowCreateModal(false);
      loadTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create task');
    }
  };

  const getTasksByStatus = (status: string) =>
    tasks.filter(t => {
      if (filter.priority && t.priority !== filter.priority) return false;
      if (filter.assignee && !t.assignee.includes(filter.assignee)) return false;
      return t.status === status;
    });

  const priorityColor = (p: string) => {
    switch (p) {
      case 'urgent': return '#ef4444';
      case 'high': return '#f97316';
      case 'medium': return '#f59e0b';
      case 'low': return '#10b981';
      default: return '#6b7280';
    }
  };

  const columnCounts = DEFAULT_COLUMNS.map(col => ({
    ...col,
    count: getTasksByStatus(col.status).length,
  }));

  if (loading) {
    return <div className="panel-loading">Loading board...</div>;
  }

  return (
    <div className="kanban-board">
      <div className="board-header">
        <h2>Task Board</h2>
        <div className="board-actions">
          <select
            value={filter.priority}
            onChange={e => setFilter(f => ({ ...f, priority: e.target.value }))}
          >
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            + New Task
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {/* Column Summary */}
      <div className="board-stats">
        {columnCounts.map(col => (
          <div key={col.id} className="board-stat" style={{ borderTopColor: col.color }}>
            <span className="stat-count">{col.count}</span>
            <span className="stat-label">{col.title}</span>
          </div>
        ))}
      </div>

      {/* Board Columns */}
      <div className="board-columns">
        {DEFAULT_COLUMNS.map(column => {
          const columnTasks = getTasksByStatus(column.status);
          return (
            <div
              key={column.id}
              className="board-column"
              onDragOver={e => e.preventDefault()}
              onDrop={() => handleDrop(column.status)}
              style={{ borderTopColor: column.color }}
            >
              <div className="column-header">
                <h3 style={{ color: column.color }}>{column.title}</h3>
                <span className="column-count">{columnTasks.length}</span>
              </div>
              <div className="column-tasks">
                {columnTasks.map(task => (
                  <div
                    key={task.id}
                    className={`task-card ${dragTask === task.id ? 'dragging' : ''}`}
                    draggable
                    onDragStart={() => handleDragStart(task.id)}
                    onDragEnd={() => setDragTask(null)}
                  >
                    <div className="task-priority" style={{ background: priorityColor(task.priority) }} />
                    <div className="task-content">
                      <h4 className="task-title">{task.title}</h4>
                      {task.description && (
                        <p className="task-description">{task.description.slice(0, 100)}</p>
                      )}
                      <div className="task-meta">
                        {task.labels && task.labels.length > 0 && (
                          <div className="task-labels">
                            {task.labels.slice(0, 3).map((label, i) => (
                              <span key={i} className="label-tag">{label}</span>
                            ))}
                          </div>
                        )}
                        {task.assignee && (
                          <span className="task-assignee" title={task.assignee}>
                            {task.assignee.slice(0, 2).toUpperCase()}
                          </span>
                        )}
                        {task.blocked_by && task.blocked_by.length > 0 && (
                          <span className="task-blocked" title="Blocked">
                            🚫
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {columnTasks.length === 0 && (
                  <div className="column-empty">Drop tasks here</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Create Task Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Create New Task</h3>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                value={newTask.title}
                onChange={e => setNewTask({ ...newTask, title: e.target.value })}
                placeholder="Task title..."
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                value={newTask.description}
                onChange={e => setNewTask({ ...newTask, description: e.target.value })}
                placeholder="Task description..."
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Priority</label>
              <select
                value={newTask.priority}
                onChange={e => setNewTask({ ...newTask, priority: e.target.value })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div className="form-group">
              <label>Labels (comma-separated)</label>
              <input
                type="text"
                value={newTask.labels}
                onChange={e => setNewTask({ ...newTask, labels: e.target.value })}
                placeholder="frontend, bug, feature..."
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleCreateTask}>
                Create Task
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};