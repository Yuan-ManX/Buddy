import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface ExperimentStats {
  total_experiments: number;
  active_experiments: number;
  completed_experiments: number;
  total_trials: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}

interface ExperimentInfo {
  experiment_id: string;
  name: string;
  description: string;
  experiment_type: string;
  status: string;
  control: { variant_id: string; config: Record<string, unknown> };
  treatment: { variant_id: string; config: Record<string, unknown> };
  metrics: Array<{ name: string; type: string; target: number }>;
  trial_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface TrialResult {
  trial_id: string;
  variant_id: string;
  metrics: Record<string, number>;
  success: boolean;
  context: Record<string, unknown> | null;
  timestamp: string;
}

interface ExperimentAnalysis {
  experiment_id: string;
  control_metrics: Record<string, { mean: number; std: number; count: number }>;
  treatment_metrics: Record<string, { mean: number; std: number; count: number }>;
  improvements: Record<string, { absolute: number; relative: number; significant: boolean }>;
  winner: string | null;
  confidence: number;
  recommendation: string;
}

export const ExperimentPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<ExperimentStats | null>(null);
  const [experiments, setExperiments] = useState<ExperimentInfo[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<ExperimentInfo | null>(null);
  const [analysis, setAnalysis] = useState<ExperimentAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'detail' | 'analysis'>('overview');

  // Create form
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    experiment_type: 'ab_test',
    control_prompt: '',
    treatment_prompt: '',
    control_config: '{}',
    treatment_config: '{}',
    task_description: '',
  });

  // Trial recording form
  const [trialForm, setTrialForm] = useState({
    variant_id: '',
    metrics: '{}',
    success: true,
    error_message: '',
  });

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch('/api/experiments/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to load experiment stats:', e); }
  }, []);

  const loadExperiments = useCallback(async () => {
    try {
      const res = await fetch('/api/experiments');
      setExperiments((await res.json()).experiments || []);
    } catch (e) { console.error('Failed to load experiments:', e); }
  }, []);

  useEffect(() => {
    loadStats();
    loadExperiments();
    setLoading(false);
  }, [loadStats, loadExperiments]);

  const handleCreate = async () => {
    try {
      const res = await fetch('/api/experiments/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: createForm.name,
          description: createForm.description,
          experiment_type: createForm.experiment_type,
          control_config: JSON.parse(createForm.control_config || '{}'),
          treatment_config: JSON.parse(createForm.treatment_config || '{}'),
          metrics: [],
        }),
      });
      const exp = await res.json();
      toast.success('Experiment created');
      setCreateForm({ name: '', description: '', experiment_type: 'ab_test', control_prompt: '', treatment_prompt: '', control_config: '{}', treatment_config: '{}', task_description: '' });
      loadExperiments();
      loadStats();
    } catch (e: any) {
      toast.error('Failed to create: ' + e.message);
    }
  };

  const handleCreatePromptAB = async () => {
    try {
      const res = await fetch('/api/experiments/prompt-ab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: createForm.name,
          description: createForm.description,
          control_prompt: createForm.control_prompt,
          treatment_prompt: createForm.treatment_prompt,
          task_description: createForm.task_description,
        }),
      });
      const exp = await res.json();
      toast.success('Prompt A/B test created');
      setCreateForm({ name: '', description: '', experiment_type: 'ab_test', control_prompt: '', treatment_prompt: '', control_config: '{}', treatment_config: '{}', task_description: '' });
      loadExperiments();
      loadStats();
    } catch (e: any) {
      toast.error('Failed: ' + e.message);
    }
  };

  const handleStart = async (expId: string) => {
    try {
      await fetch(`/api/experiments/${expId}/start`, { method: 'POST' });
      toast.success('Experiment started');
      loadExperiments();
    } catch (e: any) {
      toast.error('Failed: ' + e.message);
    }
  };

  const handleComplete = async (expId: string) => {
    try {
      await fetch(`/api/experiments/${expId}/complete`, { method: 'POST' });
      toast.success('Experiment completed');
      loadExperiments();
    } catch (e: any) {
      toast.error('Failed: ' + e.message);
    }
  };

  const handleViewAnalysis = async (expId: string) => {
    try {
      const res = await fetch(`/api/experiments/${expId}/analysis`);
      setAnalysis(await res.json());
      setActiveSection('analysis');
    } catch (e: any) {
      toast.error('Failed to load analysis: ' + e.message);
    }
  };

  const handleRecordTrial = async () => {
    if (!selectedExperiment) return;
    try {
      await fetch(`/api/experiments/${selectedExperiment.experiment_id}/trials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          variant_id: trialForm.variant_id,
          metrics: JSON.parse(trialForm.metrics || '{}'),
          success: trialForm.success,
          error_message: trialForm.error_message || undefined,
        }),
      });
      toast.success('Trial recorded');
      loadExperiments();
    } catch (e: any) {
      toast.error('Failed: ' + e.message);
    }
  };

  if (loading) return <div className="panel-loading">Loading...</div>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Experiment Tracker</h2>
        <div className="panel-tabs">
          <button className={`tab-btn ${activeSection === 'overview' ? 'active' : ''}`} onClick={() => setActiveSection('overview')}>Overview</button>
          <button className={`tab-btn ${activeSection === 'create' ? 'active' : ''}`} onClick={() => setActiveSection('create')}>Create</button>
          <button className={`tab-btn ${activeSection === 'detail' ? 'active' : ''}`} onClick={() => setActiveSection('detail')}>Detail</button>
          <button className={`tab-btn ${activeSection === 'analysis' ? 'active' : ''}`} onClick={() => setActiveSection('analysis')}>Analysis</button>
        </div>
      </div>

      <div className="panel-body">
        {activeSection === 'overview' && (
          <div>
            {stats && (
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{stats.total_experiments}</div>
                  <div className="stat-label">Total Experiments</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.active_experiments}</div>
                  <div className="stat-label">Active</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.completed_experiments}</div>
                  <div className="stat-label">Completed</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.total_trials}</div>
                  <div className="stat-label">Total Trials</div>
                </div>
              </div>
            )}

            <h3>Experiments</h3>
            <div className="list-container">
              {experiments.length === 0 ? (
                <div className="empty-state">No experiments yet. Create one to start testing.</div>
              ) : (
                experiments.map((exp) => (
                  <div key={exp.experiment_id} className="list-item">
                    <div className="list-item-main">
                      <div className="list-item-title">{exp.name}</div>
                      <div className="list-item-subtitle">{exp.description}</div>
                      <div className="list-item-meta">
                        <span className={`badge badge-${exp.status}`}>{exp.status}</span>
                        <span className="badge">{exp.experiment_type}</span>
                        <span>{exp.trial_count} trials</span>
                      </div>
                    </div>
                    <div className="list-item-actions">
                      {exp.status === 'created' && (
                        <button className="btn-sm btn-primary" onClick={() => handleStart(exp.experiment_id)}>Start</button>
                      )}
                      {exp.status === 'running' && (
                        <button className="btn-sm btn-success" onClick={() => handleComplete(exp.experiment_id)}>Complete</button>
                      )}
                      <button className="btn-sm btn-secondary" onClick={() => { setSelectedExperiment(exp); setActiveSection('detail'); }}>View</button>
                      <button className="btn-sm btn-secondary" onClick={() => handleViewAnalysis(exp.experiment_id)}>Analyze</button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeSection === 'create' && (
          <div className="form-container">
            <h3>Create Experiment</h3>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} placeholder="Experiment name" />
            </div>
            <div className="form-group">
              <label>Description</label>
              <input type="text" value={createForm.description} onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })} placeholder="Brief description" />
            </div>
            <div className="form-group">
              <label>Type</label>
              <select value={createForm.experiment_type} onChange={(e) => setCreateForm({ ...createForm, experiment_type: e.target.value })}>
                <option value="ab_test">A/B Test</option>
                <option value="multivariate">Multivariate</option>
                <option value="prompt_ab">Prompt A/B</option>
                <option value="config_ab">Config A/B</option>
              </select>
            </div>

            <h4>Prompt A/B Test</h4>
            <div className="form-group">
              <label>Control Prompt</label>
              <textarea value={createForm.control_prompt} onChange={(e) => setCreateForm({ ...createForm, control_prompt: e.target.value })} rows={3} placeholder="Original prompt" />
            </div>
            <div className="form-group">
              <label>Treatment Prompt</label>
              <textarea value={createForm.treatment_prompt} onChange={(e) => setCreateForm({ ...createForm, treatment_prompt: e.target.value })} rows={3} placeholder="Variant prompt" />
            </div>
            <div className="form-group">
              <label>Task Description</label>
              <input type="text" value={createForm.task_description} onChange={(e) => setCreateForm({ ...createForm, task_description: e.target.value })} placeholder="What task to test" />
            </div>
            <button className="btn-primary" onClick={handleCreatePromptAB} disabled={!createForm.name}>Create Prompt A/B Test</button>

            <h4>Config A/B Test</h4>
            <div className="form-group">
              <label>Control Config (JSON)</label>
              <textarea value={createForm.control_config} onChange={(e) => setCreateForm({ ...createForm, control_config: e.target.value })} rows={3} placeholder='{"temperature": 0.7}' />
            </div>
            <div className="form-group">
              <label>Treatment Config (JSON)</label>
              <textarea value={createForm.treatment_config} onChange={(e) => setCreateForm({ ...createForm, treatment_config: e.target.value })} rows={3} placeholder='{"temperature": 0.3}' />
            </div>
            <button className="btn-primary" onClick={handleCreate} disabled={!createForm.name}>Create Config A/B Test</button>
          </div>
        )}

        {activeSection === 'detail' && selectedExperiment && (
          <div className="detail-container">
            <h3>{selectedExperiment.name}</h3>
            <p>{selectedExperiment.description}</p>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Status</span>
                <span className={`badge badge-${selectedExperiment.status}`}>{selectedExperiment.status}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Type</span>
                <span>{selectedExperiment.experiment_type}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Trials</span>
                <span>{selectedExperiment.trial_count}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Created</span>
                <span>{new Date(selectedExperiment.created_at).toLocaleString()}</span>
              </div>
            </div>

            <h4>Record Trial</h4>
            <div className="form-group">
              <label>Variant ID</label>
              <select value={trialForm.variant_id} onChange={(e) => setTrialForm({ ...trialForm, variant_id: e.target.value })}>
                <option value="">Select variant</option>
                <option value={selectedExperiment.control?.variant_id}>Control</option>
                <option value={selectedExperiment.treatment?.variant_id}>Treatment</option>
              </select>
            </div>
            <div className="form-group">
              <label>Metrics (JSON)</label>
              <textarea value={trialForm.metrics} onChange={(e) => setTrialForm({ ...trialForm, metrics: e.target.value })} rows={2} placeholder='{"latency_ms": 250, "accuracy": 0.95}' />
            </div>
            <div className="form-group">
              <label>
                <input type="checkbox" checked={trialForm.success} onChange={(e) => setTrialForm({ ...trialForm, success: e.target.checked })} />
                Success
              </label>
            </div>
            <button className="btn-primary" onClick={handleRecordTrial} disabled={!trialForm.variant_id}>Record Trial</button>
          </div>
        )}

        {activeSection === 'analysis' && analysis && (
          <div className="analysis-container">
            <h3>Experiment Analysis</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{analysis.confidence.toFixed(1)}%</div>
                <div className="stat-label">Confidence</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{analysis.winner || 'TBD'}</div>
                <div className="stat-label">Winner</div>
              </div>
            </div>

            <h4>Recommendation</h4>
            <p className="recommendation-text">{analysis.recommendation}</p>

            <h4>Metric Comparison</h4>
            <div className="metrics-table">
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Control Mean</th>
                    <th>Treatment Mean</th>
                    <th>Improvement</th>
                    <th>Significant</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(analysis.improvements || {}).map(([metric, imp]) => (
                    <tr key={metric}>
                      <td>{metric}</td>
                      <td>{analysis.control_metrics?.[metric]?.mean?.toFixed(3) || '-'}</td>
                      <td>{analysis.treatment_metrics?.[metric]?.mean?.toFixed(3) || '-'}</td>
                      <td className={imp.relative > 0 ? 'positive' : 'negative'}>
                        {imp.relative > 0 ? '+' : ''}{imp.relative.toFixed(1)}%
                      </td>
                      <td>{imp.significant ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};