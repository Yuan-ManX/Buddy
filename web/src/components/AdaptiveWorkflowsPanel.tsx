import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface AdaptiveWorkflow {
  workflow_id: string;
  name: string;
  description: string;
  template_id: string;
  status: string;
  step_count: number;
  current_step: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

interface WorkflowTemplate {
  template_id: string;
  name: string;
  description: string;
  category: string;
  default_step_count: number;
  version: string;
  tags: string[];
  created_at: string;
}

interface AdaptiveWorkflowStats {
  total_workflows: number;
  active_workflows: number;
  completed_workflows: number;
  failed_workflows: number;
  total_templates: number;
  average_completion_time_ms: number;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const AdaptiveWorkflowsPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<AdaptiveWorkflowStats | null>(null);
  const [workflows, setWorkflows] = useState<AdaptiveWorkflow[]>([]);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'workflows' | 'templates' | 'execute'>('overview');

  // Create workflow form
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    template_id: '',
    parameters: '',
  });
  const [creating, setCreating] = useState(false);

  // Execute form
  const [executeForm, setExecuteForm] = useState({
    workflow_id: '',
    input_data: '',
  });
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, w, t] = await Promise.all([
        request<AdaptiveWorkflowStats>('/adaptive-workflows/stats').catch(() => null),
        request<AdaptiveWorkflow[]>('/adaptive-workflows/workflows').catch(() => []),
        request<WorkflowTemplate[]>('/adaptive-workflows/templates').catch(() => []),
      ]);
      setStats(s);
      setWorkflows(Array.isArray(w) ? w : (w as any)?.workflows || []);
      setTemplates(Array.isArray(t) ? t : (t as any)?.templates || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load adaptive workflows data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateWorkflow = async () => {
    if (!createForm.name.trim()) return;
    try {
      setCreating(true);
      const result = await request<any>('/adaptive-workflows/workflows', {
        method: 'POST',
        body: JSON.stringify({
          name: createForm.name,
          description: createForm.description || undefined,
          template_id: createForm.template_id || undefined,
          parameters: createForm.parameters
            ? JSON.parse(createForm.parameters)
            : undefined,
        }),
      });
      toast.success(result.message || 'Workflow created successfully');
      setCreateForm({ name: '', description: '', template_id: '', parameters: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleExecute = async () => {
    if (!executeForm.workflow_id.trim()) return;
    try {
      setExecuting(true);
      setExecuteResult(null);
      const result = await request<any>(`/adaptive-workflows/workflows/${executeForm.workflow_id}/execute`, {
        method: 'POST',
        body: JSON.stringify({
          input_data: executeForm.input_data || undefined,
        }),
      });
      setExecuteResult(result);
      toast.success(result.message || 'Workflow executed successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setExecuting(false);
    }
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    running: '#3b82f6',
    completed: '#22c55e',
    failed: '#ef4444',
    paused: '#f59e0b',
    pending: '#9ca3af',
    draft: '#9ca3af',
  };

  const templateCategoryColors: Record<string, string> = {
    automation: '#4f6ef7',
    data: '#22c55e',
    integration: '#8b5cf6',
    deployment: '#f59e0b',
    monitoring: '#06b6d4',
    general: '#9ca3af',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Adaptive Workflows</h2>
          <p className="panel-subtitle">Create, manage, and execute adaptive workflows</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading adaptive workflows data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Adaptive Workflows</h2>
        <p className="panel-subtitle">Dynamic workflow creation, template-based generation, and execution engine</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_workflows}</span>
              <span className="stat-label">Total Workflows</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_workflows}</span>
              <span className="stat-label">Active</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.completed_workflows}</span>
              <span className="stat-label">Completed</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#ef4444' }}>{stats.failed_workflows}</span>
              <span className="stat-label">Failed</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.total_templates}</span>
              <span className="stat-label">Templates</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'workflows', 'templates', 'execute'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Workflows Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Workflows</span>
                <strong>{stats.total_workflows}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Active Workflows</span>
                <strong style={{ color: '#22c55e' }}>{stats.active_workflows}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Completed</span>
                <strong style={{ color: '#3b82f6' }}>{stats.completed_workflows}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Failed</span>
                <strong style={{ color: '#ef4444' }}>{stats.failed_workflows}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Templates</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.total_templates}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Avg Completion Time</span>
                <strong>{stats.average_completion_time_ms?.toFixed(1)}ms</strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Recent Workflows</h3>
              {workflows.length === 0 ? (
                <div className="panel-empty">No workflows created yet</div>
              ) : (
                <div className="forge-skill-list">
                  {workflows.slice(0, 5).map(wf => (
                    <div key={wf.workflow_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{wf.name}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[wf.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {wf.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{wf.description}</div>
                        <div>Steps: {wf.current_step}/{wf.step_count}</div>
                        <div>Created: {new Date(wf.created_at).toLocaleString()}</div>
                        {wf.completed_at && (
                          <div>Completed: {new Date(wf.completed_at).toLocaleString()}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <h3 style={{ marginTop: 24 }}>Available Templates</h3>
              {templates.length === 0 ? (
                <div className="panel-empty">No templates available</div>
              ) : (
                <div className="forge-skill-list">
                  {templates.slice(0, 3).map(tmpl => (
                    <div key={tmpl.template_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{tmpl.name}</div>
                        <span className="dashboard-badge" style={{
                          background: templateCategoryColors[tmpl.category] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {tmpl.category}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{tmpl.description}</div>
                        <div>Steps: {tmpl.default_step_count} | Version: {tmpl.version}</div>
                        {tmpl.tags && (
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                            {tmpl.tags.map((tag, i) => (
                              <span key={i} style={{
                                padding: '2px 8px',
                                background: '#e8eaf6',
                                color: '#4f6ef7',
                                borderRadius: 12,
                                fontSize: '0.7rem',
                              }}>
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Create Section ── */}
      {activeSection === 'create' && (
        <div className="dashboard-section">
          <h3>Create Workflow</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Workflow Name</label>
              <input
                type="text"
                value={createForm.name}
                onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Adaptive Workflow"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={2}
                value={createForm.description}
                onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this workflow does"
              />
            </div>
            <div className="form-group">
              <label>Template</label>
              <select
                value={createForm.template_id}
                onChange={e => setCreateForm(f => ({ ...f, template_id: e.target.value }))}
              >
                <option value="">No Template (Custom)</option>
                {templates.map(t => (
                  <option key={t.template_id} value={t.template_id}>{t.name} ({t.category})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Parameters (JSON)</label>
              <textarea
                rows={3}
                value={createForm.parameters}
                onChange={e => setCreateForm(f => ({ ...f, parameters: e.target.value }))}
                placeholder='{"input_path": "/data/source", "output_format": "json"}'
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleCreateWorkflow}
              disabled={creating || !createForm.name.trim()}
            >
              {creating ? 'Creating...' : 'Create Workflow'}
            </button>
          </div>
        </div>
      )}

      {/* ── Workflows Section ── */}
      {activeSection === 'workflows' && (
        <div className="dashboard-section">
          <h3>Workflows ({workflows.length})</h3>
          {workflows.length === 0 ? (
            <div className="panel-empty">No workflows yet. Go to the Create tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {workflows.map(wf => (
                <div key={wf.workflow_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{wf.name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[wf.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {wf.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{wf.description}</div>
                    <div style={{ marginTop: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: '0.85rem', color: '#6b7280', minWidth: 60 }}>
                          Progress
                        </span>
                        <div style={{
                          flex: 1,
                          height: 8,
                          background: '#e5e7eb',
                          borderRadius: 4,
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${wf.step_count > 0 ? (wf.current_step / wf.step_count) * 100 : 0}%`,
                            height: '100%',
                            background: wf.status === 'completed' ? '#22c55e' : '#3b82f6',
                            borderRadius: 4,
                            transition: 'width 0.3s ease',
                          }} />
                        </div>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                          {wf.current_step}/{wf.step_count}
                        </span>
                      </div>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      Template: {wf.template_id || 'Custom'}
                    </div>
                    <div>Created: {new Date(wf.created_at).toLocaleString()}</div>
                    <div>Updated: {new Date(wf.updated_at).toLocaleString()}</div>
                    {wf.completed_at && (
                      <div>Completed: {new Date(wf.completed_at).toLocaleString()}</div>
                    )}
                    <div>Workflow ID: {wf.workflow_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Templates Section ── */}
      {activeSection === 'templates' && (
        <div className="dashboard-section">
          <h3>Workflow Templates ({templates.length})</h3>
          {templates.length === 0 ? (
            <div className="panel-empty">No templates available</div>
          ) : (
            <div className="forge-skill-list">
              {templates.map(tmpl => (
                <div key={tmpl.template_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{tmpl.name}</div>
                    <span className="dashboard-badge" style={{
                      background: templateCategoryColors[tmpl.category] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {tmpl.category}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{tmpl.description}</div>
                    <div>Steps: {tmpl.default_step_count} | Version: {tmpl.version}</div>
                    {tmpl.tags && tmpl.tags.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                        {tmpl.tags.map((tag, i) => (
                          <span key={i} style={{
                            padding: '2px 8px',
                            background: '#e8eaf6',
                            color: '#4f6ef7',
                            borderRadius: 12,
                            fontSize: '0.7rem',
                          }}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <div>Created: {new Date(tmpl.created_at).toLocaleString()}</div>
                    <div>Template ID: {tmpl.template_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Execute Section ── */}
      {activeSection === 'execute' && (
        <div className="dashboard-section">
          <h3>Execute Workflow</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Workflow</label>
              <select
                value={executeForm.workflow_id}
                onChange={e => setExecuteForm(f => ({ ...f, workflow_id: e.target.value }))}
              >
                <option value="">Select a workflow...</option>
                {workflows.map(wf => (
                  <option key={wf.workflow_id} value={wf.workflow_id}>
                    {wf.name} ({wf.status})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Input Data (JSON)</label>
              <textarea
                rows={4}
                value={executeForm.input_data}
                onChange={e => setExecuteForm(f => ({ ...f, input_data: e.target.value }))}
                placeholder='{"key": "value"}'
                style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleExecute}
              disabled={executing || !executeForm.workflow_id.trim()}
              style={{ background: '#06b6d4' }}
            >
              {executing ? 'Executing...' : 'Execute Workflow'}
            </button>
          </div>

          {executeResult && (
            <div style={{
              marginTop: 20,
              padding: 16,
              background: '#f8fafc',
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}>
              <h4>Execution Result</h4>
              <div style={{ marginTop: 8, fontSize: '0.9rem', color: '#475569' }}>
                {executeResult.status && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Status:</strong>{' '}
                    <span className="dashboard-badge" style={{
                      background: statusColors[executeResult.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {executeResult.status}
                    </span>
                  </div>
                )}
                {executeResult.steps_completed !== undefined && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Steps Completed:</strong> {executeResult.steps_completed}
                  </div>
                )}
                {executeResult.duration_ms !== undefined && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Duration:</strong> {executeResult.duration_ms}ms
                  </div>
                )}
                {executeResult.output && (
                  <div style={{ marginTop: 8, padding: 8, background: '#fff', borderRadius: 4, border: '1px solid #e2e8f0' }}>
                    <strong>Output:</strong>
                    <pre style={{ marginTop: 4, fontSize: '0.85rem', whiteSpace: 'pre-wrap', overflow: 'auto', maxHeight: 200 }}>
                      {typeof executeResult.output === 'string' ? executeResult.output : JSON.stringify(executeResult.output, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdaptiveWorkflowsPanel;