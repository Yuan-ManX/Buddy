import React, { useState, useEffect } from 'react';
import type { Agent, AutopilotConfig } from '../types';
import { api } from '../api/client';

interface AutopilotPanelProps {
  agent: Agent;
}

const TRIGGER_LABELS: Record<string, string> = {
  interval: 'Interval',
  cron: 'Cron',
  webhook: 'Webhook',
  manual: 'Manual',
};

const STATUS_COLORS: Record<string, string> = {
  active: '#10b981',
  paused: '#f59e0b',
  completed: '#6366f1',
  failed: '#ef4444',
};

export const AutopilotPanel: React.FC<AutopilotPanelProps> = ({ agent }) => {
  const [autopilots, setAutopilots] = useState<AutopilotConfig[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    name: '',
    description: '',
    task_template: '',
    trigger: 'interval',
    schedule: '3600',
    max_runs: 0,
  });

  useEffect(() => {
    loadData();
  }, [agent.id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await api.autopilots.list(agent.id);
      setAutopilots(data);
    } catch (err) {
      console.error('Failed to load autopilots:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!form.name.trim() || !form.task_template.trim()) return;
    try {
      await api.autopilots.create({
        agent_id: agent.id,
        name: form.name,
        task_template: form.task_template,
        trigger: form.trigger,
        schedule: form.schedule,
        max_runs: form.max_runs,
        description: form.description,
      });
      setShowCreate(false);
      setForm({ name: '', description: '', task_template: '', trigger: 'interval', schedule: '3600', max_runs: 0 });
      loadData();
    } catch (err) {
      console.error('Failed to create autopilot:', err);
    }
  };

  const handlePause = async (id: string) => {
    try {
      await api.autopilots.pause(id);
      loadData();
    } catch (err) {
      console.error('Failed to pause:', err);
    }
  };

  const handleResume = async (id: string) => {
    try {
      await api.autopilots.resume(id);
      loadData();
    } catch (err) {
      console.error('Failed to resume:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this autopilot?')) return;
    try {
      await api.autopilots.delete(id);
      loadData();
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-loading">Loading autopilots...</div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Autopilot — {agent.name}</h2>
          <span className="panel-subtitle">
            {autopilots.length} scheduled tasks
          </span>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>
          + New Autopilot
        </button>
      </div>

      {showCreate && (
        <div className="autopilot-create-form">
          <h3>Create Scheduled Task</h3>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              placeholder="e.g., Daily Summary"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Description</label>
            <input
              type="text"
              placeholder="What does this task do?"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Task Template</label>
            <textarea
              placeholder="Describe what the agent should do..."
              value={form.task_template}
              onChange={(e) => setForm({ ...form, task_template: e.target.value })}
              rows={3}
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Trigger</label>
              <select
                value={form.trigger}
                onChange={(e) => setForm({ ...form, trigger: e.target.value })}
              >
                <option value="interval">Interval (seconds)</option>
                <option value="cron">Cron Expression</option>
                <option value="manual">Manual</option>
              </select>
            </div>
            <div className="form-group">
              <label>Schedule</label>
              <input
                type="text"
                placeholder="3600"
                value={form.schedule}
                onChange={(e) => setForm({ ...form, schedule: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Max Runs (0=unlimited)</label>
              <input
                type="number"
                value={form.max_runs}
                onChange={(e) => setForm({ ...form, max_runs: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>
          <div className="modal-actions">
            <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            <button className="btn-primary" onClick={handleCreate}>Create</button>
          </div>
        </div>
      )}

      <div className="autopilot-list">
        {autopilots.map((ap) => (
          <div key={ap.id} className={`autopilot-card ${ap.status}`}>
            <div className="autopilot-card-header">
              <div className="autopilot-card-status" style={{ background: STATUS_COLORS[ap.status] }}>
                {ap.status}
              </div>
              <span className="autopilot-card-trigger">{TRIGGER_LABELS[ap.trigger] || ap.trigger}</span>
              <span className="autopilot-card-runs">
                Run {ap.run_count}{ap.max_runs > 0 ? `/${ap.max_runs}` : ''}
              </span>
            </div>
            <div className="autopilot-card-name">{ap.name}</div>
            {ap.description && (
              <div className="autopilot-card-desc">{ap.description}</div>
            )}
            <div className="autopilot-card-template">
              <strong>Task:</strong> {ap.task_template}
            </div>
            <div className="autopilot-card-actions">
              {ap.status === 'active' && (
                <button className="btn-sm" onClick={() => handlePause(ap.id)}>Pause</button>
              )}
              {ap.status === 'paused' && (
                <button className="btn-sm btn-success" onClick={() => handleResume(ap.id)}>Resume</button>
              )}
              <button className="btn-sm btn-danger" onClick={() => handleDelete(ap.id)}>Delete</button>
            </div>
            <div className="autopilot-card-time">
              Created {new Date(ap.created_at).toLocaleString()}
              {ap.last_run_at && ` · Last run ${new Date(ap.last_run_at).toLocaleString()}`}
            </div>
          </div>
        ))}

        {autopilots.length === 0 && (
          <div className="panel-empty">
            No scheduled tasks. Create an autopilot to run background tasks automatically.
          </div>
        )}
      </div>
    </div>
  );
};