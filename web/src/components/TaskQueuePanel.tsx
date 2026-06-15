import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { QueuedJob, BatchJobInfo, TaskQueueStats } from '../types';

export const TaskQueuePanel: React.FC = () => {
  const [jobs, setJobs] = useState<QueuedJob[]>([]);
  const [batches, setBatches] = useState<BatchJobInfo[]>([]);
  const [stats, setStats] = useState<TaskQueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [showSubmit, setShowSubmit] = useState(false);
  const [showBatch, setShowBatch] = useState(false);
  const [submitForm, setSubmitForm] = useState({
    name: '', job_type: 'custom', payload: '{}', priority: 'normal', agent_id: '', max_retries: '3', timeout_seconds: '300', tags: '',
  });
  const [batchForm, setBatchForm] = useState({
    name: '', priority: 'normal', agent_id: '',
    jobs: JSON.stringify([{ name: 'Task 1', job_type: 'custom', payload: {} }]),
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [j, b, s] = await Promise.all([
        api.taskQueue.listJobs({ status: statusFilter || undefined, priority: priorityFilter || undefined }),
        api.taskQueue.listBatches(20),
        api.taskQueue.stats(),
      ]);
      setJobs(j.jobs);
      setBatches(b.batches);
      setStats(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load task queue');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter]);

  useEffect(() => { loadData(); const interval = setInterval(loadData, 5000); return () => clearInterval(interval); }, [loadData]);

  const handleSubmit = async () => {
    if (!submitForm.name) return;
    try {
      await api.taskQueue.submit({
        name: submitForm.name,
        job_type: submitForm.job_type,
        payload: JSON.parse(submitForm.payload),
        priority: submitForm.priority,
        agent_id: submitForm.agent_id,
        max_retries: Number(submitForm.max_retries),
        timeout_seconds: Number(submitForm.timeout_seconds),
        tags: submitForm.tags ? submitForm.tags.split(',').map(s => s.trim()) : [],
      });
      setShowSubmit(false);
      setSubmitForm({ name: '', job_type: 'custom', payload: '{}', priority: 'normal', agent_id: '', max_retries: '3', timeout_seconds: '300', tags: '' });
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit job');
    }
  };

  const handleBatchSubmit = async () => {
    if (!batchForm.name) return;
    try {
      await api.taskQueue.submitBatch({
        name: batchForm.name,
        jobs: JSON.parse(batchForm.jobs),
        priority: batchForm.priority,
        agent_id: batchForm.agent_id,
      });
      setShowBatch(false);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit batch');
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try { await api.taskQueue.cancelJob(jobId); loadData(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Failed to cancel job'); }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      queued: 'badge-gray',
      running: 'badge-blue',
      completed: 'badge-green',
      failed: 'badge-red',
      cancelled: 'badge-yellow',
    };
    return colors[status] || 'badge-gray';
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      critical: 'badge-red',
      high: 'badge-orange',
      normal: 'badge-blue',
      low: 'badge-gray',
      background: 'badge-gray',
    };
    return colors[priority] || 'badge-gray';
  };

  if (loading && jobs.length === 0) return <div className="panel-loading">Loading task queue...</div>;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Task Queue</h2>
        <div className="panel-header-actions">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="form-select">
            <option value="">All Statuses</option>
            <option value="queued">Queued</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="form-select">
            <option value="">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
          <button className="btn-primary" onClick={() => setShowSubmit(true)}>Submit Job</button>
          <button className="btn-secondary" onClick={() => setShowBatch(true)}>Batch Submit</button>
          <button className="btn-secondary" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_jobs}</div>
            <div className="stat-label">Total Jobs</div>
          </div>
          {Object.entries(stats.by_status).map(([status, count]) => (
            <div className="stat-card" key={status}>
              <div className="stat-value">{count}</div>
              <div className="stat-label">{status}</div>
            </div>
          ))}
          <div className="stat-card">
            <div className="stat-value">{stats.max_concurrent}</div>
            <div className="stat-label">Max Concurrent</div>
          </div>
        </div>
      )}

      {batches.length > 0 && (
        <div className="panel-section">
          <h3>Batches</h3>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Jobs</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((b) => (
                  <tr key={b.id}>
                    <td className="item-name">{b.name}</td>
                    <td><span className={`badge ${getStatusBadge(b.status)}`}>{b.status}</span></td>
                    <td>
                      <div className="progress-bar-mini">
                        <div className="progress-fill" style={{ width: `${b.progress * 100}%` }} />
                      </div>
                      {(b.progress * 100).toFixed(0)}% ({b.completed_jobs}/{b.total_jobs})
                    </td>
                    <td>{b.failed_jobs > 0 && <span className="badge badge-red">{b.failed_jobs} failed</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Job</th>
              <th>Type</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Agent</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>
                  <div className="item-name">{job.name}</div>
                  <div className="item-desc">{job.id}</div>
                  {job.tags.slice(0, 2).map(t => <span key={t} className="badge badge-sm">{t}</span>)}
                </td>
                <td>{job.job_type}</td>
                <td><span className={`badge ${getPriorityBadge(job.priority)}`}>{job.priority}</span></td>
                <td><span className={`badge ${getStatusBadge(job.status)}`}>{job.status}</span></td>
                <td>
                  {job.status === 'running' && (
                    <div className="progress-bar-mini">
                      <div className="progress-fill" style={{ width: `${job.progress * 100}%` }} />
                    </div>
                  )}
                  {job.status === 'running' ? `${(job.progress * 100).toFixed(0)}%` : job.status === 'completed' ? '100%' : '-'}
                </td>
                <td>{job.agent_id ? job.agent_id.slice(0, 8) : '-'}</td>
                <td>
                  {(job.status === 'queued' || job.status === 'running') && (
                    <button className="btn-sm btn-red" onClick={() => handleCancelJob(job.id)}>Cancel</button>
                  )}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr><td colSpan={7} className="empty-cell">No jobs in queue.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showSubmit && (
        <div className="modal-overlay" onClick={() => setShowSubmit(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Submit Job</h2>
            <div className="form-group">
              <label>Name (required)</label>
              <input type="text" value={submitForm.name} onChange={e => setSubmitForm({...submitForm, name: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Job Type</label>
              <select value={submitForm.job_type} onChange={e => setSubmitForm({...submitForm, job_type: e.target.value})}>
                <option value="custom">Custom</option>
                <option value="chat">Chat</option>
                <option value="analysis">Analysis</option>
                <option value="generation">Generation</option>
                <option value="task">Task</option>
              </select>
            </div>
            <div className="form-group">
              <label>Priority</label>
              <select value={submitForm.priority} onChange={e => setSubmitForm({...submitForm, priority: e.target.value})}>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
                <option value="background">Background</option>
              </select>
            </div>
            <div className="form-group">
              <label>Agent ID</label>
              <input type="text" value={submitForm.agent_id} onChange={e => setSubmitForm({...submitForm, agent_id: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Payload (JSON)</label>
              <textarea rows={3} value={submitForm.payload} onChange={e => setSubmitForm({...submitForm, payload: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Max Retries</label>
              <input type="number" value={submitForm.max_retries} onChange={e => setSubmitForm({...submitForm, max_retries: e.target.value})} min="0" />
            </div>
            <div className="form-group">
              <label>Tags (comma separated)</label>
              <input type="text" value={submitForm.tags} onChange={e => setSubmitForm({...submitForm, tags: e.target.value})} />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowSubmit(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleSubmit}>Submit</button>
            </div>
          </div>
        </div>
      )}

      {showBatch && (
        <div className="modal-overlay" onClick={() => setShowBatch(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Submit Batch</h2>
            <div className="form-group">
              <label>Batch Name (required)</label>
              <input type="text" value={batchForm.name} onChange={e => setBatchForm({...batchForm, name: e.target.value})} />
            </div>
            <div className="form-group">
              <label>Priority</label>
              <select value={batchForm.priority} onChange={e => setBatchForm({...batchForm, priority: e.target.value})}>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div className="form-group">
              <label>Jobs (JSON array)</label>
              <textarea rows={6} value={batchForm.jobs} onChange={e => setBatchForm({...batchForm, jobs: e.target.value})} />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowBatch(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleBatchSubmit}>Submit Batch</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};