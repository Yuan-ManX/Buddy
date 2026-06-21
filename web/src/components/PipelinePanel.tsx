import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface Pipeline {
  pipeline_id: string;
  name: string;
  description: string;
  pipeline_type: string;
  status: string;
  stages: { stage_id: string; name: string; status: string; error?: string }[];
  current_stage_index: number;
  version: number;
  tags: string[];
}

interface PipelineProgress {
  pipeline_id: string;
  name: string;
  status: string;
  progress: number;
  current_stage: number;
  total_stages: number;
  stages: { stage_id: string; name: string; status: string; error?: string }[];
}

export const PipelinePanel: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [progress, setProgress] = useState<PipelineProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createType, setCreateType] = useState('training');
  const [createDescription, setCreateDescription] = useState('');

  const loadPipelines = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.pipeline.list();
      setPipelines(res.pipelines || []);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPipelines(); }, [loadPipelines]);

  const loadProgress = async (pipelineId: string) => {
    try {
      const res = await api.pipeline.progress(pipelineId);
      setProgress(res);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleSelect = (pipeline: Pipeline) => {
    setSelectedPipeline(pipeline);
    loadProgress(pipeline.pipeline_id);
  };

  const handleCreate = async () => {
    if (!createName.trim()) return;
    try {
      await api.pipeline.create({
        name: createName.trim(),
        pipeline_type: createType,
        description: createDescription,
      });
      setShowCreate(false);
      setCreateName('');
      setCreateDescription('');
      loadPipelines();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleExecute = async (pipelineId: string) => {
    try {
      setLoading(true);
      await api.pipeline.execute(pipelineId);
      loadPipelines();
      loadProgress(pipelineId);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (pipelineId: string) => {
    try {
      await api.pipeline.cancel(pipelineId);
      loadPipelines();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (pipelineId: string) => {
    if (!confirm('Delete this pipeline?')) return;
    try {
      await api.pipeline.delete(pipelineId);
      setSelectedPipeline(null);
      setProgress(null);
      loadPipelines();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const typeOptions = ['training', 'fine_tuning', 'deployment', 'evaluation', 'data_processing', 'profile_sync', 'knowledge_ingestion', 'custom'];

  const statusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'var(--green)';
      case 'running': return 'var(--blue)';
      case 'failed': return 'var(--red)';
      case 'paused': return 'var(--yellow)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div className="pipeline-panel">
      <div className="panel-header">
        <h2>Pipeline Engine</h2>
        <span className="panel-subtitle">Training, Deployment & Data Pipeline Management</span>
      </div>

      {error && <div className="panel-error">{error}<button onClick={() => setError(null)}>Dismiss</button></div>}

      <div className="panel-actions">
        <button className="btn-primary" onClick={() => setShowCreate(true)}>+ New Pipeline</button>
      </div>

      {showCreate && (
        <div className="create-form">
          <h3>Create Pipeline</h3>
          <input className="input" placeholder="Pipeline name" value={createName} onChange={e => setCreateName(e.target.value)} />
          <select className="input" value={createType} onChange={e => setCreateType(e.target.value)}>
            {typeOptions.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <textarea className="input" placeholder="Description" value={createDescription} onChange={e => setCreateDescription(e.target.value)} rows={2} />
          <div className="form-actions">
            <button className="btn-primary" onClick={handleCreate}>Create</button>
            <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="pipeline-list">
        {loading && <div className="loading">Loading pipelines...</div>}
        {pipelines.map(p => (
          <div
            key={p.pipeline_id}
            className={`pipeline-card ${selectedPipeline?.pipeline_id === p.pipeline_id ? 'selected' : ''}`}
            onClick={() => handleSelect(p)}
          >
            <div className="pipeline-card-header">
              <span className="pipeline-name">{p.name}</span>
              <span className="pipeline-type-badge">{p.pipeline_type}</span>
            </div>
            <div className="pipeline-card-meta">
              <span className="pipeline-status" style={{ color: statusColor(p.status) }}>{p.status}</span>
              <span className="pipeline-stages">{p.stages.length} stages</span>
            </div>
          </div>
        ))}
      </div>

      {selectedPipeline && progress && (
        <div className="pipeline-detail">
          <h3>{selectedPipeline.name}</h3>
          <p>{selectedPipeline.description}</p>

          <div className="progress-section">
            <div className="progress-header">
              <span>Progress: {progress.progress}%</span>
              <span style={{ color: statusColor(progress.status) }}>{progress.status}</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress.progress}%` }} />
            </div>
          </div>

          <div className="stage-list">
            <h4>Stages</h4>
            {progress.stages.map((stage, i) => (
              <div key={stage.stage_id} className={`stage-item ${stage.status}`}>
                <div className="stage-indicator">
                  <span className="stage-num">{i + 1}</span>
                  <span className="stage-status-icon">
                    {stage.status === 'completed' ? '✓' : stage.status === 'running' ? '◌' : stage.status === 'failed' ? '✗' : '○'}
                  </span>
                </div>
                <div className="stage-info">
                  <span className="stage-name">{stage.name}</span>
                  <span className="stage-status-text">{stage.status}</span>
                  {stage.error && <span className="stage-error">{stage.error}</span>}
                </div>
              </div>
            ))}
          </div>

          <div className="detail-actions">
            {selectedPipeline.status === 'draft' || selectedPipeline.status === 'queued' ? (
              <button className="btn-primary" onClick={() => handleExecute(selectedPipeline.pipeline_id)}>
                Execute Pipeline
              </button>
            ) : null}
            {selectedPipeline.status === 'running' ? (
              <button className="btn-secondary" onClick={() => handleCancel(selectedPipeline.pipeline_id)}>
                Cancel
              </button>
            ) : null}
            <button className="btn-danger" onClick={() => handleDelete(selectedPipeline.pipeline_id)}>
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
};