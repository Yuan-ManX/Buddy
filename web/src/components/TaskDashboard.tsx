import React, { useState } from 'react';
import type { Agent, Task } from '../types';
import { api } from '../api/client';

interface TaskDashboardProps {
  agent: Agent;
  tasks: Task[];
  onTaskCreated: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  queued: '#6366f1',
  dispatched: '#3b82f6',
  running: '#f59e0b',
  completed: '#10b981',
  failed: '#ef4444',
  cancelled: '#6b7280',
};

const STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  dispatched: 'Dispatched',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

export const TaskDashboard: React.FC<TaskDashboardProps> = ({ agent, tasks, onTaskCreated }) => {
  const [showNewTask, setShowNewTask] = useState(false);
  const [newTask, setNewTask] = useState({ title: '', kind: 'direct', payload: '' });
  const [creating, setCreating] = useState(false);

  const handleCreateTask = async () => {
    if (!newTask.title.trim()) return;
    setCreating(true);
    try {
      let payload: Record<string, unknown> | undefined;
      if (newTask.payload.trim()) {
        try {
          payload = JSON.parse(newTask.payload);
        } catch {
          payload = { input: newTask.payload };
        }
      }
      await api.tasks.create({
        agent_id: agent.id,
        title: newTask.title,
        kind: newTask.kind,
        payload,
      });
      setNewTask({ title: '', kind: 'direct', payload: '' });
      setShowNewTask(false);
      onTaskCreated();
    } catch (err) {
      console.error('Failed to create task:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleTransition = async (taskId: string, status: string, result?: Record<string, unknown>, error?: string) => {
    try {
      await api.tasks.transition(taskId, status, result, error);
      onTaskCreated();
    } catch (err) {
      console.error('Failed to transition task:', err);
    }
  };

  const handleCancel = async (taskId: string) => {
    try {
      await api.tasks.cancel(taskId);
      onTaskCreated();
    } catch (err) {
      console.error('Failed to cancel task:', err);
    }
  };

  const activeTasks = tasks.filter((t) => !['completed', 'failed', 'cancelled'].includes(t.status));
  const completedTasks = tasks.filter((t) => ['completed', 'failed', 'cancelled'].includes(t.status));

  return (
    <div className="task-dashboard">
      <div className="task-header">
        <div className="task-header-info">
          <h2>Tasks for {agent.name}</h2>
          <span className="task-count">{activeTasks.length} active, {completedTasks.length} completed</span>
        </div>
        <button className="btn-primary" onClick={() => setShowNewTask(true)}>
          + New Task
        </button>
      </div>

      {showNewTask && (
        <div className="task-create-form">
          <h3>Create Task</h3>
          <div className="form-group">
            <label>Title</label>
            <input
              type="text"
              placeholder="What should the agent do?"
              value={newTask.title}
              onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Kind</label>
            <select value={newTask.kind} onChange={(e) => setNewTask({ ...newTask, kind: e.target.value })}>
              <option value="direct">Direct</option>
              <option value="chat">Chat</option>
              <option value="autopilot">Autopilot</option>
              <option value="quick">Quick</option>
            </select>
          </div>
          <div className="form-group">
            <label>Payload (JSON)</label>
            <textarea
              placeholder='e.g., {"file": "main.py"}'
              value={newTask.payload}
              onChange={(e) => setNewTask({ ...newTask, payload: e.target.value })}
              rows={3}
            />
          </div>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setShowNewTask(false)}>Cancel</button>
            <button className="btn-primary" onClick={handleCreateTask} disabled={creating}>
              {creating ? 'Creating...' : 'Create Task'}
            </button>
          </div>
        </div>
      )}

      {tasks.length === 0 && (
        <div className="task-empty">
          <p>No tasks yet. Create one to assign work to {agent.name}.</p>
        </div>
      )}

      <div className="task-list">
        {activeTasks.map((task) => (
          <div key={task.id} className="task-card">
            <div className="task-card-header">
              <div className="task-card-status" style={{ background: STATUS_COLORS[task.status] }}>
                {STATUS_LABELS[task.status]}
              </div>
              <span className="task-card-kind">{task.kind}</span>
              <span className="task-card-attempt">
                Attempt {task.attempt + 1}/{task.max_attempts}
              </span>
            </div>
            <div className="task-card-title">{task.title}</div>
            {task.payload && Object.keys(task.payload).length > 0 && (
              <div className="task-card-payload">
                {JSON.stringify(task.payload).slice(0, 100)}
              </div>
            )}
            <div className="task-card-actions">
              {task.status === 'queued' && (
                <button className="btn-sm" onClick={() => handleTransition(task.id, 'dispatched')}>Claim</button>
              )}
              {task.status === 'dispatched' && (
                <button className="btn-sm" onClick={() => handleTransition(task.id, 'running')}>Start</button>
              )}
              {task.status === 'running' && (
                <>
                  <button className="btn-sm btn-success" onClick={() => handleTransition(task.id, 'completed')}>Complete</button>
                  <button className="btn-sm btn-danger" onClick={() => handleTransition(task.id, 'failed', undefined, 'task_error')}>Fail</button>
                </>
              )}
              <button className="btn-sm btn-danger" onClick={() => handleCancel(task.id)}>Cancel</button>
            </div>
            <div className="task-card-time">
              Created {new Date(task.created_at).toLocaleString()}
              {task.started_at && ` · Started ${new Date(task.started_at).toLocaleString()}`}
            </div>
          </div>
        ))}

        {completedTasks.map((task) => (
          <div key={task.id} className={`task-card task-card-done ${task.status}`}>
            <div className="task-card-header">
              <div className="task-card-status" style={{ background: STATUS_COLORS[task.status] }}>
                {STATUS_LABELS[task.status]}
              </div>
              <span className="task-card-kind">{task.kind}</span>
            </div>
            <div className="task-card-title">{task.title}</div>
            {task.result && (
              <div className="task-card-result">
                Result: {JSON.stringify(task.result).slice(0, 100)}
              </div>
            )}
            {task.error && (
              <div className="task-card-error">
                Error: {task.error}
              </div>
            )}
            <div className="task-card-time">
              {task.completed_at && `Completed ${new Date(task.completed_at).toLocaleString()}`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};