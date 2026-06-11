import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Agent, SwarmSession, SwarmTask, SwarmStats } from '../types';

interface Props {
  agents: Agent[];
}

export const SwarmPanel: React.FC<Props> = ({ agents }) => {
  const [sessions, setSessions] = useState<SwarmSession[]>([]);
  const [stats, setStats] = useState<SwarmStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formState, setFormState] = useState({
    name: '',
    goal: '',
    min_members: 2,
  });
  const [executingSessions, setExecutingSessions] = useState<Set<string>>(new Set());
  const [expandedSession, setExpandedSession] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [sessionsRes, statsRes] = await Promise.all([
        api.swarm.list(),
        api.swarm.stats(),
      ]);
      setSessions(sessionsRes.sessions || []);
      setStats(statsRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load swarm data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFormSwarm = async () => {
    if (!formState.name.trim() || !formState.goal.trim()) return;
    try {
      setError(null);
      await api.swarm.form({
        name: formState.name.trim(),
        goal: formState.goal.trim(),
        min_members: formState.min_members,
      });
      setShowForm(false);
      setFormState({ name: '', goal: '', min_members: 2 });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to form swarm');
    }
  };

  const handlePlanTasks = async (sessionId: string) => {
    try {
      setError(null);
      await api.swarm.plan(sessionId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to plan tasks');
    }
  };

  const handleExecute = async (sessionId: string) => {
    try {
      setError(null);
      setExecutingSessions(prev => new Set(prev).add(sessionId));
      await api.swarm.execute(sessionId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute swarm');
    } finally {
      setExecutingSessions(prev => {
        const next = new Set(prev);
        next.delete(sessionId);
        return next;
      });
    }
  };

  const toggleExpand = (sessionId: string) => {
    setExpandedSession(prev => prev === sessionId ? null : sessionId);
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      forming: '#f59e0b',
      planning: '#8b5cf6',
      executing: '#3b82f6',
      reviewing: '#06b6d4',
      complete: '#22c55e',
      failed: '#ef4444',
      pending: '#6b7280',
      idle: '#6b7280',
      working: '#3b82f6',
      done: '#22c55e',
    };
    return (
      <span className="swarm-status-badge" style={{ background: colors[status] || '#6b7280' }}>
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-header"><h2>Swarm Engine</h2></div>
        <div className="panel-loading">Loading swarm sessions...</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Swarm Engine</h2>
        <div className="panel-actions">
          <button className="btn-sm btn-primary" onClick={() => setShowForm(true)}>
            + New Swarm
          </button>
          <button className="btn-sm btn-secondary" onClick={loadData}>
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="panel-error">
          {error}
          <button className="btn-sm" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {stats && (
        <div className="swarm-stats-row">
          <div className="swarm-stat">
            <span className="swarm-stat-value">{stats.total_sessions}</span>
            <span className="swarm-stat-label">Total Sessions</span>
          </div>
          <div className="swarm-stat">
            <span className="swarm-stat-value">{stats.active_sessions}</span>
            <span className="swarm-stat-label">Active</span>
          </div>
          <div className="swarm-stat">
            <span className="swarm-stat-value">{stats.completed_sessions}</span>
            <span className="swarm-stat-label">Completed</span>
          </div>
          <div className="swarm-stat">
            <span className="swarm-stat-value">{stats.failed_sessions}</span>
            <span className="swarm-stat-label">Failed</span>
          </div>
          <div className="swarm-stat">
            <span className="swarm-stat-value">{stats.average_members}</span>
            <span className="swarm-stat-label">Avg Members</span>
          </div>
        </div>
      )}

      {showForm && (
        <div className="swarm-form-overlay" onClick={() => setShowForm(false)}>
          <div className="swarm-form" onClick={e => e.stopPropagation()}>
            <h3>Form New Swarm</h3>
            <div className="form-group">
              <label>Swarm Name</label>
              <input
                type="text"
                value={formState.name}
                onChange={e => setFormState(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Code Review Squad"
                className="form-input"
              />
            </div>
            <div className="form-group">
              <label>Goal</label>
              <textarea
                value={formState.goal}
                onChange={e => setFormState(prev => ({ ...prev, goal: e.target.value }))}
                placeholder="Describe the goal this swarm needs to achieve..."
                className="form-input"
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Minimum Members: {formState.min_members}</label>
              <input
                type="range"
                min={1}
                max={Math.min(10, agents.length)}
                value={formState.min_members}
                onChange={e => setFormState(prev => ({ ...prev, min_members: Number(e.target.value) }))}
                className="form-range"
              />
            </div>
            <div className="form-group">
              <label>Available Agents: {agents.length}</label>
            </div>
            <div className="form-actions">
              <button className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
              <button
                className="btn-primary"
                onClick={handleFormSwarm}
                disabled={!formState.name.trim() || !formState.goal.trim()}
              >
                Form Swarm
              </button>
            </div>
          </div>
        </div>
      )}

      {sessions.length === 0 ? (
        <div className="panel-empty">
          <p>No swarm sessions yet.</p>
          <p>Form a swarm to enable collaborative agent execution.</p>
        </div>
      ) : (
        <div className="swarm-sessions-list">
          {sessions.map(session => (
            <div key={session.session_id} className="swarm-session-card">
              <div className="swarm-session-header" onClick={() => toggleExpand(session.session_id)}>
                <div className="swarm-session-info">
                  <span className="swarm-session-name">{session.name}</span>
                  <span className="swarm-session-goal">{session.goal}</span>
                </div>
                <div className="swarm-session-meta">
                  {getStatusBadge(session.status)}
                  <span className="swarm-session-members">
                    {session.members?.length || 0} members
                  </span>
                  <span className="swarm-expand-icon">
                    {expandedSession === session.session_id ? '▾' : '▸'}
                  </span>
                </div>
              </div>

              {expandedSession === session.session_id && (
                <div className="swarm-session-detail">
                  <div className="swarm-members-section">
                    <h4>Members</h4>
                    <div className="swarm-members-grid">
                      {session.members?.map(member => (
                        <div key={member.agent_id} className="swarm-member-chip">
                          <span className="swarm-member-name">{member.agent_name}</span>
                          <span className="swarm-member-role">{member.role}</span>
                          {getStatusBadge(member.status)}
                        </div>
                      ))}
                    </div>
                  </div>

                  {session.tasks && session.tasks.length > 0 && (
                    <div className="swarm-tasks-section">
                      <h4>Tasks ({session.tasks.length})</h4>
                      <div className="swarm-tasks-list">
                        {session.tasks.map((task: SwarmTask) => (
                          <div key={task.id} className="swarm-task-item">
                            <div className="swarm-task-header">
                              <span className="swarm-task-description">{task.description}</span>
                              {getStatusBadge(task.status)}
                            </div>
                            <div className="swarm-task-meta">
                              <span>Priority: {task.priority}</span>
                              {task.required_roles?.length > 0 && (
                                <span>Roles: {task.required_roles.join(', ')}</span>
                              )}
                              {task.dependencies?.length > 0 && (
                                <span>Deps: {task.dependencies.length}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {session.results && session.results.length > 0 && (
                    <div className="swarm-results-section">
                      <h4>Results</h4>
                      {session.results.map((result, idx) => (
                        <div key={idx} className="swarm-result-item">
                          <span className="swarm-result-task">Task: {result.task_id}</span>
                          <p className="swarm-result-content">{result.result}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="swarm-session-actions">
                    {session.status === 'forming' && (
                      <button
                        className="btn-primary"
                        onClick={() => handlePlanTasks(session.session_id)}
                      >
                        Plan Tasks
                      </button>
                    )}
                    {(session.status === 'planning' || session.status === 'planned') && (
                      <button
                        className="btn-primary"
                        onClick={() => handleExecute(session.session_id)}
                        disabled={executingSessions.has(session.session_id)}
                      >
                        {executingSessions.has(session.session_id) ? 'Executing...' : 'Execute'}
                      </button>
                    )}
                    {session.status === 'executing' && (
                      <div className="swarm-executing-indicator">
                        <div className="swarm-spinner" />
                        <span>Executing tasks...</span>
                      </div>
                    )}
                    {session.status === 'complete' && (
                      <span className="swarm-complete-badge">Completed</span>
                    )}
                    {session.status === 'failed' && (
                      <span className="swarm-failed-badge">Failed</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};