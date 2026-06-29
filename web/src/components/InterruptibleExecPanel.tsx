import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#dc2626',
  secondary: '#fca5a5',
  bg: '#fef2f2',
  border: '#fecaca',
  accent: '#fee2e2',
  text: '#7f1d1d',
};

const PRIORITIES = ['critical', 'high', 'normal', 'low', 'background'];
const CANCEL_REASONS = ['user_request', 'timeout', 'parent_cancelled', 'resource_limit', 'policy_violation', 'dependency_failed', 'system_shutdown', 'preempted'];
const CANCEL_SCOPES = ['self', 'children', 'entire_tree'];
const CHECKPOINT_TYPES = ['pre_step', 'post_step', 'pre_tool', 'post_tool', 'pre_model', 'post_model', 'on_error', 'user_defined'];

const stateColors: Record<string, string> = {
  running: '#22c55e',
  paused: '#eab308',
  cancelled: '#9ca3af',
  completed: '#9ca3af',
  failed: '#ef4444',
  pending: '#3b82f6',
};

export const InterruptibleExecPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'register' | 'control' | 'checkpoint'>('overview');

  // Executions list & selection
  const [executions, setExecutions] = useState<any[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<any | null>(null);

  // Register form
  const [registerForm, setRegisterForm] = useState({
    name: '',
    description: '',
    agent_id: '',
    priority: 'normal',
    timeout_seconds: '',
    total_steps: '',
  });

  // Checkpoint form
  const [checkpointForm, setCheckpointForm] = useState({
    checkpoint_type: 'pre_step',
    step_index: '',
    step_description: '',
    state: '',
  });
  const [checkResult, setCheckResult] = useState<any>(null);

  // Cancel form
  const [cancelForm, setCancelForm] = useState({
    reason: 'user_request',
    scope: 'self',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, list] = await Promise.all([
        api.interruptibleExec.stats(),
        api.interruptibleExec.list({ limit: 50 }),
      ]);
      setStats(s);
      setExecutions(Array.isArray(list) ? list : (list as any)?.executions || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load interruptible executor data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const reloadAndReselect = async (executionId?: string) => {
    await loadData();
    if (executionId) {
      try {
        const updated = await api.interruptibleExec.get(executionId);
        setSelectedExecution(updated);
      } catch (e: any) {
        toast.error(e.message);
      }
    }
  };

  const handleRegister = async () => {
    if (!registerForm.name.trim()) return;
    try {
      await api.interruptibleExec.register({
        name: registerForm.name.trim(),
        description: registerForm.description.trim() || undefined,
        agent_id: registerForm.agent_id.trim() || undefined,
        priority: registerForm.priority,
        timeout_seconds: registerForm.timeout_seconds ? Number(registerForm.timeout_seconds) : undefined,
        total_steps: Number(registerForm.total_steps) || 0,
      });
      toast.success(`Execution "${registerForm.name}" registered`);
      setRegisterForm({
        name: '',
        description: '',
        agent_id: '',
        priority: 'normal',
        timeout_seconds: '',
        total_steps: '',
      });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleSelect = async (id: string) => {
    try {
      const exec = await api.interruptibleExec.get(id);
      setSelectedExecution(exec);
      setCheckResult(null);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleStart = async () => {
    if (!selectedExecution) return;
    try {
      await api.interruptibleExec.start(selectedExecution.execution_id);
      toast.success('Execution started');
      await reloadAndReselect(selectedExecution.execution_id);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleComplete = async () => {
    if (!selectedExecution) return;
    try {
      await api.interruptibleExec.complete(selectedExecution.execution_id);
      toast.success('Execution completed');
      await reloadAndReselect(selectedExecution.execution_id);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handlePause = async () => {
    if (!selectedExecution) return;
    try {
      await api.interruptibleExec.pause(selectedExecution.execution_id);
      toast.success('Execution paused');
      await reloadAndReselect(selectedExecution.execution_id);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleResume = async () => {
    if (!selectedExecution) return;
    try {
      await api.interruptibleExec.resume(selectedExecution.execution_id);
      toast.success('Execution resumed');
      await reloadAndReselect(selectedExecution.execution_id);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCancel = async () => {
    if (!selectedExecution) return;
    try {
      await api.interruptibleExec.cancel(selectedExecution.execution_id, { ...cancelForm });
      toast.success('Execution cancelled');
      await reloadAndReselect(selectedExecution.execution_id);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCheckpoint = async () => {
    if (!selectedExecution) return;
    try {
      const parsedState = checkpointForm.state ? JSON.parse(checkpointForm.state) : {};
      await api.interruptibleExec.checkpoint(selectedExecution.execution_id, {
        checkpoint_type: checkpointForm.checkpoint_type,
        step_index: Number(checkpointForm.step_index) || 0,
        step_description: checkpointForm.step_description,
        state: parsedState,
      });
      toast.success('Checkpoint saved');
      setCheckpointForm({
        checkpoint_type: 'pre_step',
        step_index: '',
        step_description: '',
        state: '',
      });
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCheck = async () => {
    if (!selectedExecution) return;
    try {
      const result = await api.interruptibleExec.check(selectedExecution.execution_id);
      setCheckResult(result);
      toast.success('Execution status checked');
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2 style={{ color: themeColors.primary }}>⏸️ Interruptible Executor</h2>
          <p className="panel-subtitle">Manage cancellable, pausable, checkpointable agent executions</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading interruptible executor...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container forge-panel" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2 style={{ color: themeColors.primary }}>⏸️ Interruptible Executor</h2>
        <p className="panel-subtitle">Manage cancellable, pausable, checkpointable agent executions</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_executions ?? '-'}</span><span className="stat-label">Executions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_checkpoints ?? '-'}</span><span className="stat-label">Checkpoints</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_cancellations ?? '-'}</span><span className="stat-label">Cancellations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_duration ?? '-'}</span><span className="stat-label">Avg Duration</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'register', 'control', 'checkpoint'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Section */}
      {activeSection === 'overview' && (
        <div className="dashboard-section forge-section">
          {stats && (
            <div className="forge-grid" style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              <div className="forge-stat forge-card" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Executions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_executions ?? 0}</div>
              </div>
              <div className="forge-stat forge-card" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Checkpoints</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_checkpoints ?? 0}</div>
              </div>
              <div className="forge-stat forge-card" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Cancellations</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_cancellations ?? 0}</div>
              </div>
              <div className="forge-stat forge-card" style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Duration</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_duration ?? 0}</div>
              </div>
            </div>
          )}

          <h3 style={{ color: themeColors.text }}>Executions</h3>
          {executions.length === 0 ? (
            <div className="panel-empty">No executions registered yet</div>
          ) : (
            <table className="forge-table" style={{ width: '100%', borderCollapse: 'collapse', border: `1px solid ${themeColors.border}` }}>
              <thead>
                <tr style={{ background: themeColors.accent }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Execution ID</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Name</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>State</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Priority</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Started At</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {executions.map((exec) => {
                  const stateLower = (exec.state || '').toLowerCase();
                  const stateColor = stateColors[stateLower] || '#9ca3af';
                  const isSelected = selectedExecution?.execution_id === exec.execution_id;
                  return (
                    <tr key={exec.execution_id} style={{ background: isSelected ? themeColors.accent : '#fff', borderBottom: `1px solid ${themeColors.border}` }}>
                      <td style={{ padding: '8px 12px', fontSize: '0.85rem', fontFamily: 'monospace' }}>{exec.execution_id}</td>
                      <td style={{ padding: '8px 12px' }}>{exec.name}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <span style={{ padding: '2px 8px', borderRadius: 12, background: stateColor, color: '#fff', fontSize: '0.75rem', fontWeight: 600 }}>
                          {exec.state}
                        </span>
                      </td>
                      <td style={{ padding: '8px 12px' }}>{exec.priority ?? '-'}</td>
                      <td style={{ padding: '8px 12px', fontSize: '0.85rem' }}>{exec.started_at ? new Date(exec.started_at).toLocaleString() : '-'}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <button
                          className="forge-btn btn-sm"
                          style={{ background: themeColors.primary, color: '#fff' }}
                          onClick={() => handleSelect(exec.execution_id)}
                        >
                          Select
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Register Section */}
      {activeSection === 'register' && (
        <div className="dashboard-section forge-section">
          <h3 style={{ color: themeColors.text }}>Register Execution</h3>
          <div className="skill-execute forge-form" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  className="forge-input"
                  value={registerForm.name}
                  onChange={e => setRegisterForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. research-task-1"
                />
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input
                  type="text"
                  className="forge-input"
                  value={registerForm.agent_id}
                  onChange={e => setRegisterForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="Optional agent ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                className="forge-input"
                value={registerForm.description}
                onChange={e => setRegisterForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the execution goal..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Priority</label>
                <select className="forge-select" value={registerForm.priority} onChange={e => setRegisterForm(f => ({ ...f, priority: e.target.value }))}>
                  {PRIORITIES.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Timeout (seconds)</label>
                <input
                  type="number"
                  min="0"
                  className="forge-input"
                  value={registerForm.timeout_seconds}
                  onChange={e => setRegisterForm(f => ({ ...f, timeout_seconds: e.target.value }))}
                  placeholder="Optional"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Total Steps</label>
              <input
                type="number"
                min="0"
                className="forge-input"
                value={registerForm.total_steps}
                onChange={e => setRegisterForm(f => ({ ...f, total_steps: e.target.value }))}
                placeholder="e.g. 10"
              />
            </div>
            <button
              className="btn-primary forge-btn"
              style={{ background: themeColors.primary }}
              onClick={handleRegister}
              disabled={!registerForm.name.trim()}
            >
              Register Execution
            </button>
          </div>
        </div>
      )}

      {/* Control Section */}
      {activeSection === 'control' && (
        <div className="dashboard-section forge-section">
          <h3 style={{ color: themeColors.text }}>Execution Control</h3>
          {!selectedExecution ? (
            <div className="panel-empty">Select an execution from the Overview tab first.</div>
          ) : (
            <>
              <div className="forge-card" style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h4 style={{ color: themeColors.text }}>Execution Details</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8, marginTop: 8 }}>
                  <div><strong style={{ color: themeColors.text }}>Execution ID:</strong> <span style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{selectedExecution.execution_id}</span></div>
                  <div><strong style={{ color: themeColors.text }}>Name:</strong> {selectedExecution.name}</div>
                  <div>
                    <strong style={{ color: themeColors.text }}>State:</strong>{' '}
                    <span style={{ padding: '2px 8px', borderRadius: 12, background: stateColors[(selectedExecution.state || '').toLowerCase()] || '#9ca3af', color: '#fff', fontSize: '0.75rem', fontWeight: 600 }}>
                      {selectedExecution.state}
                    </span>
                  </div>
                  <div><strong style={{ color: themeColors.text }}>Priority:</strong> {selectedExecution.priority ?? '-'}</div>
                  <div><strong style={{ color: themeColors.text }}>Started At:</strong> {selectedExecution.started_at ? new Date(selectedExecution.started_at).toLocaleString() : '-'}</div>
                  <div><strong style={{ color: themeColors.text }}>Completed At:</strong> {selectedExecution.completed_at ? new Date(selectedExecution.completed_at).toLocaleString() : '-'}</div>
                  <div><strong style={{ color: themeColors.text }}>Total Steps:</strong> {selectedExecution.total_steps ?? 0}</div>
                  <div><strong style={{ color: themeColors.text }}>Completed Steps:</strong> {selectedExecution.completed_steps ?? 0}</div>
                  <div><strong style={{ color: themeColors.text }}>Current Step:</strong> {selectedExecution.current_step ?? '-'}</div>
                  <div><strong style={{ color: themeColors.text }}>Error:</strong> {selectedExecution.error ?? '-'}</div>
                </div>
              </div>

              {/* Action buttons based on state */}
              <div className="forge-form" style={{ marginBottom: 16 }}>
                <h4 style={{ color: themeColors.text }}>Actions</h4>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                  {selectedExecution.state === 'PENDING' && (
                    <button className="forge-btn btn-primary" style={{ background: '#3b82f6', color: '#fff' }} onClick={handleStart}>
                      ▶ Start
                    </button>
                  )}
                  {selectedExecution.state === 'RUNNING' && (
                    <>
                      <button className="forge-btn btn-primary" style={{ background: '#eab308', color: '#fff' }} onClick={handlePause}>
                        ⏸ Pause
                      </button>
                      <button className="forge-btn btn-primary" style={{ background: themeColors.primary, color: '#fff' }} onClick={handleCancel}>
                        ✖ Cancel
                      </button>
                      <button className="forge-btn btn-primary" style={{ background: '#06b6d4', color: '#fff' }} onClick={handleCheck}>
                        ✓ Check
                      </button>
                    </>
                  )}
                  {selectedExecution.state === 'PAUSED' && (
                    <>
                      <button className="forge-btn btn-primary" style={{ background: '#22c55e', color: '#fff' }} onClick={handleResume}>
                        ▶ Resume
                      </button>
                      <button className="forge-btn btn-primary" style={{ background: themeColors.primary, color: '#fff' }} onClick={handleCancel}>
                        ✖ Cancel
                      </button>
                    </>
                  )}
                  {(selectedExecution.state === 'RUNNING' || selectedExecution.state === 'PAUSED') && (
                    <button className="forge-btn btn-primary" style={{ background: '#8b5cf6', color: '#fff' }} onClick={handleComplete}>
                      ✔ Complete
                    </button>
                  )}
                </div>
              </div>

              {/* Cancel form */}
              <div className="forge-form" style={{ marginBottom: 16 }}>
                <h4 style={{ color: themeColors.text }}>Cancel Options</h4>
                <div className="form-row" style={{ marginTop: 8 }}>
                  <div className="form-group">
                    <label>Reason</label>
                    <select className="forge-select" value={cancelForm.reason} onChange={e => setCancelForm(f => ({ ...f, reason: e.target.value }))}>
                      {CANCEL_REASONS.map(r => (
                        <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Scope</label>
                    <select className="forge-select" value={cancelForm.scope} onChange={e => setCancelForm(f => ({ ...f, scope: e.target.value }))}>
                      {CANCEL_SCOPES.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <button
                  className="btn-primary forge-btn"
                  style={{ background: themeColors.primary }}
                  onClick={handleCancel}
                >
                  Cancel Execution
                </button>
              </div>

              {/* Check result */}
              {checkResult && (
                <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                  <h4 style={{ color: themeColors.text }}>Check Result</h4>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(checkResult, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Checkpoint Section */}
      {activeSection === 'checkpoint' && (
        <div className="dashboard-section forge-section">
          <h3 style={{ color: themeColors.text }}>Checkpoint State</h3>
          {!selectedExecution ? (
            <div className="panel-empty">Select an execution from the Overview tab first.</div>
          ) : (
            <>
              <div className="forge-card" style={{ padding: '12px', background: themeColors.accent, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <strong style={{ color: themeColors.text }}>Target Execution:</strong>{' '}
                <span style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{selectedExecution.execution_id}</span>{' '}
                <span style={{ color: themeColors.text }}>({selectedExecution.name})</span>
              </div>

              <div className="skill-execute forge-form" style={{ marginBottom: 16, position: 'static' }}>
                <div className="form-row">
                  <div className="form-group">
                    <label>Checkpoint Type</label>
                    <select className="forge-select" value={checkpointForm.checkpoint_type} onChange={e => setCheckpointForm(f => ({ ...f, checkpoint_type: e.target.value }))}>
                      {CHECKPOINT_TYPES.map(t => (
                        <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Step Index</label>
                    <input
                      type="number"
                      min="0"
                      className="forge-input"
                      value={checkpointForm.step_index}
                      onChange={e => setCheckpointForm(f => ({ ...f, step_index: e.target.value }))}
                      placeholder="e.g. 3"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Step Description</label>
                  <input
                    type="text"
                    className="forge-input"
                    value={checkpointForm.step_description}
                    onChange={e => setCheckpointForm(f => ({ ...f, step_description: e.target.value }))}
                    placeholder="Describe what happened at this step..."
                  />
                </div>
                <div className="form-group">
                  <label>State (JSON)</label>
                  <textarea
                    rows={6}
                    className="forge-input"
                    value={checkpointForm.state}
                    onChange={e => setCheckpointForm(f => ({ ...f, state: e.target.value }))}
                    placeholder='{"key": "value", "progress": 0.5}'
                  />
                </div>
                <button
                  className="btn-primary forge-btn"
                  style={{ background: themeColors.primary }}
                  onClick={handleCheckpoint}
                >
                  Save Checkpoint
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default InterruptibleExecPanel;
