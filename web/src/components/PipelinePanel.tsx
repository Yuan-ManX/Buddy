import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface PipelineStep {
  kind: string;
  name: string;
  config: Record<string, string>;
  depends_on: string[];
}

interface Pipeline {
  id: string;
  name: string;
  description: string;
  steps: PipelineStep[];
  step_count: number;
  created_at: string;
}

interface PipelineRun {
  id: string;
  pipeline_id: string;
  pipeline_name: string;
  status: string;
  progress: number;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number;
  error?: string;
}

interface PipelineStats {
  total_pipelines: number;
  total_runs: number;
  success_rate: number;
  active_runs: number;
}

export const PipelinePanel: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'pipelines' | 'history'>('pipelines');
  const [showCreate, setShowCreate] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [runProgress, setRunProgress] = useState(0);
  const { success: showSuccess, error: showError } = useToast();

  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    steps: [{ kind: 'tool', name: '', config: '{}', depends_on: '' }] as Array<{
      kind: string;
      name: string;
      config: string;
      depends_on: string;
    }>,
  });

  const loadPipelines = useCallback(async () => {
    try {
      const data = await api.skills.list();
      setPipelines(data as unknown as Pipeline[]);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load pipelines');
    }
  }, []);

  const loadRunHistory = useCallback(async () => {
    try {
      const data = await api.trajectory.recent(50);
      setRuns(data as unknown as PipelineRun[]);
    } catch (e: any) {
      // Run history is best-effort
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const data = await api.trajectory.stats();
      setStats(data as unknown as PipelineStats);
    } catch (e: any) {
      // Stats are best-effort
    }
  }, []);

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([loadPipelines(), loadStats(), loadRunHistory()]);
      setLoading(false);
    };
    loadAll();
  }, [loadPipelines, loadStats, loadRunHistory]);

  useEffect(() => {
    loadRunHistory();
  }, [activeView, loadRunHistory]);

  const handleCreatePipeline = async () => {
    if (!createForm.name.trim()) {
      showError('Pipeline name is required');
      return;
    }

    const steps: PipelineStep[] = createForm.steps.map((s) => ({
      kind: s.kind,
      name: s.name,
      config: (() => { try { return JSON.parse(s.config); } catch { return {}; } })(),
      depends_on: s.depends_on ? s.depends_on.split(',').map((d) => d.trim()) : [],
    }));

    try {
      const data = await api.skills.pipeline(
        steps.map((s) => ({ name: s.name, params: s.config })),
        createForm.name
      );
      showSuccess('Pipeline created successfully');
      setShowCreate(false);
      setCreateForm({
        name: '',
        description: '',
        steps: [{ kind: 'tool', name: '', config: '{}', depends_on: '' }],
      });
      await loadPipelines();
      await loadStats();
    } catch (e: any) {
      showError(e.message || 'Failed to create pipeline');
    }
  };

  const handleRunPipeline = async (pipeline: Pipeline) => {
    try {
      setRunning(pipeline.id);
      setRunProgress(0);

      // Simulate progress tracking while running
      const interval = setInterval(() => {
        setRunProgress((prev) => Math.min(prev + 10, 90));
      }, 500);

      await api.skills.execute(pipeline.name, pipeline.id, {});

      clearInterval(interval);
      setRunProgress(100);
      showSuccess(`Pipeline "${pipeline.name}" completed successfully`);
      await loadRunHistory();
      await loadStats();
    } catch (e: any) {
      showError(e.message || 'Pipeline execution failed');
    } finally {
      setRunning(null);
      setRunProgress(0);
    }
  };

  const addStep = () => {
    setCreateForm({
      ...createForm,
      steps: [...createForm.steps, { kind: 'tool', name: '', config: '{}', depends_on: '' }],
    });
  };

  const removeStep = (index: number) => {
    if (createForm.steps.length <= 1) return;
    setCreateForm({
      ...createForm,
      steps: createForm.steps.filter((_, i) => i !== index),
    });
  };

  const updateStep = (index: number, field: string, value: string) => {
    const updated = [...createForm.steps];
    updated[index] = { ...updated[index], [field]: value };
    setCreateForm({ ...createForm, steps: updated });
  };

  const statusClass = (status: string): string => {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'running': return 'status-running';
      case 'failed': return 'status-failed';
      case 'pending': return 'status-pending';
      default: return '';
    }
  };

  if (loading) {
    return <div className="panel-loading">Loading pipelines...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Agent Pipelines</h2>
        <div className="panel-header-actions">
          <button
            className={`btn-sm ${activeView === 'pipelines' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveView('pipelines')}
          >
            Pipelines
          </button>
          <button
            className={`btn-sm ${activeView === 'history' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveView('history')}
          >
            Run History
          </button>
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + New Pipeline
          </button>
        </div>
      </div>

      {error && (
        <div className="panel-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>x</button>
        </div>
      )}

      {stats && (
        <div className="board-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_pipelines || pipelines.length}</span>
            <span className="stat-label">Total Pipelines</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_runs || runs.length}</span>
            <span className="stat-label">Total Runs</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">
              {stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(0)}%` : '-'}
            </span>
            <span className="stat-label">Success Rate</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.active_runs ?? 0}</span>
            <span className="stat-label">Active Runs</span>
          </div>
        </div>
      )}

      {/* Create Pipeline Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Pipeline</h2>

            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                placeholder="Pipeline name"
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                placeholder="Describe what this pipeline does..."
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                rows={2}
              />
            </div>

            <div className="form-group">
              <label>
                Steps
                <button className="btn-sm btn-secondary" onClick={addStep} style={{ marginLeft: 8 }}>
                  + Add Step
                </button>
              </label>
              {createForm.steps.map((step, idx) => (
                <div key={idx} className="step-row" style={{ marginBottom: 8, padding: 8, border: '1px solid var(--border)', borderRadius: 8 }}>
                  <div style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                    <select
                      value={step.kind}
                      onChange={(e) => updateStep(idx, 'kind', e.target.value)}
                      style={{ width: 100 }}
                    >
                      <option value="tool">Tool</option>
                      <option value="skill">Skill</option>
                      <option value="agent">Agent</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Step name"
                      value={step.name}
                      onChange={(e) => updateStep(idx, 'name', e.target.value)}
                      style={{ flex: 1 }}
                    />
                    {createForm.steps.length > 1 && (
                      <button className="btn-sm btn-danger" onClick={() => removeStep(idx)}>
                        x
                      </button>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      type="text"
                      placeholder='Config (JSON)'
                      value={step.config}
                      onChange={(e) => updateStep(idx, 'config', e.target.value)}
                      style={{ flex: 1 }}
                    />
                    <input
                      type="text"
                      placeholder="Depends on (comma-separated)"
                      value={step.depends_on}
                      onChange={(e) => updateStep(idx, 'depends_on', e.target.value)}
                      style={{ flex: 1 }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleCreatePipeline}>
                Create Pipeline
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline List View */}
      {activeView === 'pipelines' && (
        <>
          {pipelines.length === 0 ? (
            <div className="panel-empty">
              <p>No pipelines defined yet.</p>
              <p className="text-muted">Create a pipeline to orchestrate multi-step agent execution flows.</p>
            </div>
          ) : (
            <div className="pipeline-grid" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {pipelines.map((pipeline) => (
                <div key={pipeline.id} className="stat-card" style={{ textAlign: 'left' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 4 }}>
                        {pipeline.name}
                      </h3>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 8 }}>
                        {pipeline.description || 'No description'}
                      </p>
                      <div style={{ display: 'flex', gap: 16, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>Steps: {pipeline.step_count || (pipeline.steps?.length || 0)}</span>
                        <span>Created: {new Date(pipeline.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button
                      className="btn-primary btn-sm"
                      onClick={() => handleRunPipeline(pipeline)}
                      disabled={running === pipeline.id}
                    >
                      {running === pipeline.id ? 'Running...' : 'Run'}
                    </button>
                  </div>

                  {/* Steps Preview */}
                  {(pipeline.steps?.length > 0) && (
                    <div style={{ marginTop: 12, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {pipeline.steps.map((step, idx) => (
                        <span
                          key={idx}
                          style={{
                            padding: '2px 8px',
                            borderRadius: 12,
                            background: 'var(--blue-bg)',
                            color: 'var(--blue)',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                          }}
                        >
                          {step.kind}:{step.name}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Running Progress */}
                  {running === pipeline.id && (
                    <div style={{ marginTop: 12 }}>
                      <div style={{
                        height: 6,
                        background: 'var(--border-light)',
                        borderRadius: 3,
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${runProgress}%`,
                          background: 'var(--blue)',
                          borderRadius: 3,
                          transition: 'width 0.3s ease',
                        }} />
                      </div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                        {runProgress}%
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Run History View */}
      {activeView === 'history' && (
        <>
          {runs.length === 0 ? (
            <div className="panel-empty">
              <p>No pipeline runs recorded yet.</p>
              <p className="text-muted">Run a pipeline to see execution history here.</p>
            </div>
          ) : (
            <div className="pipeline-grid" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {runs.map((run) => (
                <div key={run.id} className="stat-card" style={{ textAlign: 'left' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <h4 style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                          {run.pipeline_name || run.pipeline_id}
                        </h4>
                        <span className={`status-badge ${statusClass(run.status)}`}>
                          {run.status}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
                        Started: {new Date(run.started_at).toLocaleString()}
                        {run.completed_at && (
                          <> · Duration: {(run.duration_seconds ?? 0).toFixed(1)}s</>
                        )}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--blue)' }}>
                        {run.progress != null ? `${(run.progress * 100).toFixed(0)}%` : '-'}
                      </span>
                    </div>
                  </div>
                  {run.status === 'running' && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{
                        height: 4,
                        background: 'var(--border-light)',
                        borderRadius: 2,
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${(run.progress ?? 0) * 100}%`,
                          background: 'var(--blue)',
                          borderRadius: 2,
                          transition: 'width 0.5s ease',
                        }} />
                      </div>
                    </div>
                  )}
                  {run.error && (
                    <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--red)', padding: '4px 8px', background: 'rgba(239,68,68,0.08)', borderRadius: 4 }}>
                      {run.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};