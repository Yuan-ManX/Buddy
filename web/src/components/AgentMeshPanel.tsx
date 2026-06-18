import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { MeshStatus, MeshNodeStatus, MeshEvent, MeshTask } from '../types';

export const AgentMeshPanel: React.FC = () => {
  const toast = useToast();
  const [status, setStatus] = useState<MeshStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'nodes' | 'tasks' | 'events' | 'delegate'>('overview');
  const [events, setEvents] = useState<MeshEvent[]>([]);
  const [pendingTasks, setPendingTasks] = useState<MeshTask[]>([]);
  const [strategy, setStrategy] = useState('hybrid');

  // Delegate form
  const [delegateForm, setDelegateForm] = useState({
    from_agent_id: '',
    to_agent_id: '',
    title: '',
    description: '',
    priority: 'normal',
  });

  // Register form
  const [showRegister, setShowRegister] = useState(false);
  const [registerForm, setRegisterForm] = useState({
    agent_id: '',
    agent_name: '',
    role: 'general',
    capabilities: '',
    max_concurrent_tasks: '3',
    tags: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [meshStatus, meshEvents, tasks] = await Promise.all([
        api.agentMesh.status(),
        api.agentMesh.events(50),
        api.agentMesh.pendingTasks(),
      ]);
      setStatus(meshStatus);
      setEvents(meshEvents.events);
      setPendingTasks(tasks.tasks);
      setStrategy(meshStatus.delegation_strategy);
    } catch (e: any) {
      setError(e.message || 'Failed to load mesh data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleProcessTasks = async () => {
    try {
      const result = await api.agentMesh.processTasks();
      toast.success(`Processed ${result.processed} tasks`);
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to process tasks');
    }
  };

  const handlePauseNode = async (agentId: string) => {
    try {
      await api.agentMesh.pauseNode(agentId);
      toast.success('Node paused');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to pause node');
    }
  };

  const handleResumeNode = async (agentId: string) => {
    try {
      await api.agentMesh.resumeNode(agentId);
      toast.success('Node resumed');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to resume node');
    }
  };

  const handleStrategyChange = async (newStrategy: string) => {
    try {
      await api.agentMesh.setStrategy(newStrategy);
      setStrategy(newStrategy);
      toast.success('Strategy updated');
    } catch (e: any) {
      toast.error(e.message || 'Failed to update strategy');
    }
  };

  const handleDelegate = async () => {
    if (!delegateForm.from_agent_id || !delegateForm.to_agent_id || !delegateForm.title) return;
    try {
      await api.agentMesh.delegate(delegateForm.from_agent_id, delegateForm.to_agent_id, {
        title: delegateForm.title,
        description: delegateForm.description,
        priority: delegateForm.priority,
      });
      setDelegateForm({ from_agent_id: '', to_agent_id: '', title: '', description: '', priority: 'normal' });
      toast.success('Task delegated');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Delegation failed');
    }
  };

  const handleRegisterNode = async () => {
    if (!registerForm.agent_id || !registerForm.agent_name) return;
    try {
      await api.agentMesh.registerNode({
        agent_id: registerForm.agent_id,
        agent_name: registerForm.agent_name,
        role: registerForm.role,
        capabilities: registerForm.capabilities ? registerForm.capabilities.split(',').map(c => c.trim()).filter(Boolean) : undefined,
        max_concurrent_tasks: parseInt(registerForm.max_concurrent_tasks),
        tags: registerForm.tags ? registerForm.tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
      });
      setShowRegister(false);
      setRegisterForm({ agent_id: '', agent_name: '', role: 'general', capabilities: '', max_concurrent_tasks: '3', tags: '' });
      toast.success('Node registered');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to register node');
    }
  };

  const handleSubmitTask = async () => {
    const title = prompt('Task title:');
    if (!title) return;
    const description = prompt('Task description (optional):') || '';
    const priority = prompt('Priority (critical/high/normal/low/background):') || 'normal';
    try {
      await api.agentMesh.submitTask({ title, description, priority });
      toast.success('Task submitted');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to submit task');
    }
  };

  if (loading && !status) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Agent Mesh</h2>
        </div>
        <div className="panel-loading">Loading mesh data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Agent Mesh</h2>
        </div>
        <div className="panel-error">
          <p>{error}</p>
          <button className="btn-secondary" onClick={loadData}>Retry</button>
        </div>
      </div>
    );
  }

  const getStateColor = (state: string): string => {
    switch (state) {
      case 'active': return '#22c55e';
      case 'busy': return '#f59e0b';
      case 'idle': return '#3b82f6';
      case 'paused': return '#6b7280';
      case 'degraded': return '#ef4444';
      case 'recovering': return '#f97316';
      case 'error': return '#dc2626';
      default: return '#9ca3af';
    }
  };

  const getHealthColor = (score: number): string => {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Agent Mesh</h2>
        <div className="panel-header-actions">
          <button className="btn-secondary btn-sm" onClick={loadData}>Refresh</button>
          <button className="btn-primary btn-sm" onClick={handleSubmitTask}>+ Task</button>
          <button className="btn-primary btn-sm" onClick={() => setShowRegister(true)}>+ Node</button>
        </div>
      </div>

      {/* Section Navigation */}
      <div className="panel-tabs">
        {(['overview', 'nodes', 'tasks', 'events', 'delegate'] as const).map(section => (
          <button
            key={section}
            className={`panel-tab ${activeSection === section ? 'active' : ''}`}
            onClick={() => setActiveSection(section)}
          >
            {section === 'overview' && 'Overview'}
            {section === 'nodes' && 'Nodes'}
            {section === 'tasks' && 'Tasks'}
            {section === 'events' && 'Events'}
            {section === 'delegate' && 'Delegate'}
          </button>
        ))}
      </div>

      {/* Overview Section */}
      {activeSection === 'overview' && status && (
        <div className="mesh-overview">
          <div className="mesh-stats-grid">
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.total_nodes}</div>
              <div className="mesh-stat-label">Total Nodes</div>
            </div>
            <div className="mesh-stat-card healthy">
              <div className="mesh-stat-value">{status.healthy_nodes}</div>
              <div className="mesh-stat-label">Healthy</div>
            </div>
            <div className="mesh-stat-card degraded">
              <div className="mesh-stat-value">{status.degraded_nodes}</div>
              <div className="mesh-stat-label">Degraded</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.total_tasks}</div>
              <div className="mesh-stat-label">Total Tasks</div>
            </div>
            <div className="mesh-stat-card success">
              <div className="mesh-stat-value">{status.completed_tasks}</div>
              <div className="mesh-stat-label">Completed</div>
            </div>
            <div className="mesh-stat-card error">
              <div className="mesh-stat-value">{status.failed_tasks}</div>
              <div className="mesh-stat-label">Failed</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.pending_tasks}</div>
              <div className="mesh-stat-label">Pending</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{(status.overall_success_rate * 100).toFixed(1)}%</div>
              <div className="mesh-stat-label">Success Rate</div>
            </div>
          </div>

          <div className="mesh-strategy-section">
            <h3>Delegation Strategy</h3>
            <div className="strategy-selector">
              {['capability_match', 'load_balanced', 'round_robin', 'confidence_weighted', 'hybrid'].map(s => (
                <button
                  key={s}
                  className={`strategy-btn ${strategy === s ? 'active' : ''}`}
                  onClick={() => handleStrategyChange(s)}
                >
                  {s.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Nodes Section */}
      {activeSection === 'nodes' && status && (
        <div className="mesh-nodes">
          {status.nodes.map(node => (
            <div key={node.agent_id} className="mesh-node-card">
              <div className="mesh-node-header">
                <span className="mesh-node-state" style={{ backgroundColor: getStateColor(node.state) }}>
                  {node.state}
                </span>
                <span className="mesh-node-name">{node.agent_name}</span>
                <span className="mesh-node-role">{node.role}</span>
              </div>
              <div className="mesh-node-metrics">
                <div className="mesh-metric">
                  <span className="metric-label">Health</span>
                  <span className="metric-value" style={{ color: getHealthColor(node.metrics.health_score) }}>
                    {(node.metrics.health_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="mesh-metric">
                  <span className="metric-label">Success Rate</span>
                  <span className="metric-value">{(node.metrics.success_rate * 100).toFixed(0)}%</span>
                </div>
                <div className="mesh-metric">
                  <span className="metric-label">Load</span>
                  <span className="metric-value">{node.metrics.current_load}/{node.metrics.max_concurrent}</span>
                </div>
                <div className="mesh-metric">
                  <span className="metric-label">Tasks</span>
                  <span className="metric-value">{node.metrics.total_tasks}</span>
                </div>
                <div className="mesh-metric">
                  <span className="metric-label">Cost</span>
                  <span className="metric-value">${node.metrics.total_cost.toFixed(4)}</span>
                </div>
                <div className="mesh-metric">
                  <span className="metric-label">Uptime</span>
                  <span className="metric-value">{Math.floor(node.metrics.uptime_seconds / 60)}m</span>
                </div>
              </div>
              <div className="mesh-node-capabilities">
                {node.capabilities.map(cap => (
                  <span key={cap} className="mesh-cap-tag">{cap}</span>
                ))}
              </div>
              <div className="mesh-node-actions">
                {node.state === 'active' || node.state === 'busy' ? (
                  <button className="btn-secondary btn-sm" onClick={() => handlePauseNode(node.agent_id)}>Pause</button>
                ) : node.state === 'paused' ? (
                  <button className="btn-primary btn-sm" onClick={() => handleResumeNode(node.agent_id)}>Resume</button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tasks Section */}
      {activeSection === 'tasks' && (
        <div className="mesh-tasks">
          <div className="mesh-tasks-header">
            <h3>Pending Tasks ({pendingTasks.length})</h3>
            <button className="btn-primary btn-sm" onClick={handleProcessTasks}>Process All</button>
          </div>
          {pendingTasks.length === 0 ? (
            <div className="mesh-empty">No pending tasks</div>
          ) : (
            <div className="mesh-task-list">
              {pendingTasks.map(task => (
                <div key={task.task_id} className="mesh-task-item">
                  <div className="mesh-task-title">{task.title}</div>
                  <div className="mesh-task-meta">
                    <span className={`mesh-task-priority priority-${task.priority}`}>{task.priority}</span>
                    {task.target_agent_id && (
                      <span className="mesh-task-target">Target: {task.target_agent_id}</span>
                    )}
                    <span className="mesh-task-time">{new Date(task.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Events Section */}
      {activeSection === 'events' && (
        <div className="mesh-events">
          <h3>Recent Events</h3>
          {events.length === 0 ? (
            <div className="mesh-empty">No events yet</div>
          ) : (
            <div className="mesh-event-list">
              {events.map((event, i) => (
                <div key={i} className="mesh-event-item">
                  <span className="mesh-event-type">{event.event_type}</span>
                  {event.agent_id && <span className="mesh-event-agent">{event.agent_id}</span>}
                  {event.task_id && <span className="mesh-event-task">{event.task_id}</span>}
                  <span className="mesh-event-time">{new Date(event.timestamp).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Delegate Section */}
      {activeSection === 'delegate' && (
        <div className="mesh-delegate">
          <h3>Delegate Task</h3>
          <div className="delegate-form">
            <div className="form-group">
              <label>From Agent ID</label>
              <input
                type="text"
                value={delegateForm.from_agent_id}
                onChange={e => setDelegateForm(f => ({ ...f, from_agent_id: e.target.value }))}
                placeholder="agent-strategy-001"
              />
            </div>
            <div className="form-group">
              <label>To Agent ID</label>
              <input
                type="text"
                value={delegateForm.to_agent_id}
                onChange={e => setDelegateForm(f => ({ ...f, to_agent_id: e.target.value }))}
                placeholder="agent-engineering-001"
              />
            </div>
            <div className="form-group">
              <label>Task Title</label>
              <input
                type="text"
                value={delegateForm.title}
                onChange={e => setDelegateForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Analyze the codebase..."
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                value={delegateForm.description}
                onChange={e => setDelegateForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Task description..."
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Priority</label>
              <select
                value={delegateForm.priority}
                onChange={e => setDelegateForm(f => ({ ...f, priority: e.target.value }))}
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
                <option value="background">Background</option>
              </select>
            </div>
            <button className="btn-primary" onClick={handleDelegate}>Delegate Task</button>
          </div>
        </div>
      )}

      {/* Register Node Modal */}
      {showRegister && (
        <div className="modal-overlay" onClick={() => setShowRegister(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Register Node</h3>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={registerForm.agent_id}
                onChange={e => setRegisterForm(f => ({ ...f, agent_id: e.target.value }))}
                placeholder="agent-new-001"
              />
            </div>
            <div className="form-group">
              <label>Agent Name</label>
              <input
                type="text"
                value={registerForm.agent_name}
                onChange={e => setRegisterForm(f => ({ ...f, agent_name: e.target.value }))}
                placeholder="New Agent"
              />
            </div>
            <div className="form-group">
              <label>Role</label>
              <input
                type="text"
                value={registerForm.role}
                onChange={e => setRegisterForm(f => ({ ...f, role: e.target.value }))}
                placeholder="general"
              />
            </div>
            <div className="form-group">
              <label>Capabilities (comma-separated)</label>
              <input
                type="text"
                value={registerForm.capabilities}
                onChange={e => setRegisterForm(f => ({ ...f, capabilities: e.target.value }))}
                placeholder="chat, code, research"
              />
            </div>
            <div className="form-group">
              <label>Max Concurrent Tasks</label>
              <input
                type="number"
                value={registerForm.max_concurrent_tasks}
                onChange={e => setRegisterForm(f => ({ ...f, max_concurrent_tasks: e.target.value }))}
                min="1"
                max="10"
              />
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                value={registerForm.tags}
                onChange={e => setRegisterForm(f => ({ ...f, tags: e.target.value }))}
                placeholder="production, critical"
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowRegister(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleRegisterNode}>Register</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};