import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { ScheduledTaskItem, SchedulerStats } from '../types';

const STATUS_COLORS: Record<string, string> = {
  active: '#10b981',
  paused: '#f59e0b',
  completed: '#6366f1',
  failed: '#ef4444',
  cancelled: '#9ca3af',
};

const SCHEDULE_TYPE_EMOJIS: Record<string, string> = {
  cron: '⏰',
  interval: '🔄',
  manual: '👆',
};

export const SchedulerPanel: React.FC = () => {
  const [schedules, setSchedules] = useState<ScheduledTaskItem[]>([]);
  const [stats, setStats] = useState<SchedulerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showParse, setShowParse] = useState(false);
  const [parseText, setParseText] = useState('');
  const [parseResult, setParseResult] = useState<string | null>(null);
  const [newSchedule, setNewSchedule] = useState({
    name: '', prompt: '', agent_id: '', description: '',
    cron_expression: '', interval_seconds: 3600, natural_schedule: '', tags: [] as string[],
  });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [schRes, statsRes] = await Promise.all([
        api.schedules.list(),
        api.schedules.stats(),
      ]);
      setSchedules(schRes.schedules);
      setStats(statsRes);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load scheduler data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newSchedule.name.trim() || !newSchedule.prompt.trim()) return;
    try {
      await api.schedules.create(newSchedule);
      setShowCreate(false);
      setNewSchedule({ name: '', prompt: '', agent_id: '', description: '', cron_expression: '', interval_seconds: 3600, natural_schedule: '', tags: [] });
      loadData();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handlePause = async (id: string) => {
    try { await api.schedules.pause(id); loadData(); } catch (e: any) { setError(e.message); }
  };

  const handleResume = async (id: string) => {
    try { await api.schedules.resume(id); loadData(); } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async (id: string) => {
    try { await api.schedules.delete(id); loadData(); } catch (e: any) { setError(e.message); }
  };

  const handleParse = async () => {
    if (!parseText.trim()) return;
    try {
      const result = await api.schedules.parse(parseText);
      setParseResult(JSON.stringify(result, null, 2));
    } catch (e: any) {
      setParseResult(`Error: ${e.message}`);
    }
  };

  const getStatusColor = (status: string) => STATUS_COLORS[status] || '#6b7280';
  const getTypeEmoji = (type: string) => SCHEDULE_TYPE_EMOJIS[type] || '📅';
  const formatTime = (iso: string) => iso ? new Date(iso).toLocaleString() : 'N/A';

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header"><h2>Buddy Scheduler</h2><p className="panel-subtitle">Cron-based Task Scheduling & Automation</p></div>
        <div className="panel-loading"><div className="spinner" /><span>Loading schedules...</span></div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Buddy Scheduler</h2>
        <p className="panel-subtitle">Cron-based Task Scheduling & Automation</p>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-icon">📋</span>
            <div className="stat-content"><span className="stat-value">{stats.total_tasks}</span><span className="stat-label">Total</span></div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">🟢</span>
            <div className="stat-content"><span className="stat-value" style={{ color: '#10b981' }}>{stats.active_tasks}</span><span className="stat-label">Active</span></div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">⏸️</span>
            <div className="stat-content"><span className="stat-value" style={{ color: '#f59e0b' }}>{stats.paused_tasks}</span><span className="stat-label">Paused</span></div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">✅</span>
            <div className="stat-content"><span className="stat-value">{stats.completed_tasks}</span><span className="stat-label">Completed</span></div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">{stats.engine_running ? '🟢' : '🔴'}</span>
            <div className="stat-content"><span className="stat-value" style={{ color: stats.engine_running ? '#10b981' : '#ef4444' }}>{stats.engine_running ? 'Running' : 'Stopped'}</span><span className="stat-label">Engine</span></div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="action-bar">
        <button className="btn-primary-sm" onClick={() => setShowCreate(true)}>+ New Schedule</button>
        <button className="btn-secondary-sm" onClick={() => setShowParse(true)}>🕐 Parse Schedule</button>
        <button className="btn-secondary-sm" onClick={loadData}>🔄 Refresh</button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create Schedule</h3>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={newSchedule.name} onChange={e => setNewSchedule({ ...newSchedule, name: e.target.value })} placeholder="Schedule name" autoFocus />
            </div>
            <div className="form-group">
              <label>Prompt / Task Description</label>
              <textarea rows={3} value={newSchedule.prompt} onChange={e => setNewSchedule({ ...newSchedule, prompt: e.target.value })} placeholder="What should this scheduled task do?" />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Cron Expression (optional)</label>
                <input type="text" value={newSchedule.cron_expression} onChange={e => setNewSchedule({ ...newSchedule, cron_expression: e.target.value })} placeholder="0 0 9 * * *" />
              </div>
              <div className="form-group">
                <label>Interval (seconds)</label>
                <input type="number" value={newSchedule.interval_seconds} onChange={e => setNewSchedule({ ...newSchedule, interval_seconds: Number(e.target.value) })} />
              </div>
            </div>
            <div className="form-group">
              <label>Natural Schedule (e.g. "every monday at 9am")</label>
              <input type="text" value={newSchedule.natural_schedule} onChange={e => setNewSchedule({ ...newSchedule, natural_schedule: e.target.value })} placeholder="every monday at 9am" />
            </div>
            <div className="form-group">
              <label>Agent ID (optional)</label>
              <input type="text" value={newSchedule.agent_id} onChange={e => setNewSchedule({ ...newSchedule, agent_id: e.target.value })} placeholder="agent-..." />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Parse Modal */}
      {showParse && (
        <div className="modal-overlay" onClick={() => { setShowParse(false); setParseResult(null); }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Parse Natural Schedule</h3>
            <div className="form-group">
              <label>Natural Language</label>
              <input type="text" value={parseText} onChange={e => setParseText(e.target.value)} placeholder="e.g., every monday at 9am" autoFocus />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => { setShowParse(false); setParseResult(null); }}>Close</button>
              <button className="btn-primary" onClick={handleParse}>Parse</button>
            </div>
            {parseResult && <pre className="exec-result">{parseResult}</pre>}
          </div>
        </div>
      )}

      {/* Schedule Grid */}
      {schedules.length > 0 ? (
        <div className="schedule-grid">
          {schedules.map(sch => (
            <div key={sch.id} className="schedule-card">
              <div className="schedule-card-header">
                <span className="schedule-name">{getTypeEmoji(sch.schedule_type)} {sch.name}</span>
                <span className="schedule-status" style={{ color: getStatusColor(sch.status) }}>● {sch.status}</span>
              </div>
              <div className="schedule-detail">
                <div className="schedule-meta"><span className="meta-label">Type</span><span className="meta-value">{sch.schedule_type || 'manual'}</span></div>
                {sch.cron_expression && <div className="schedule-meta"><span className="meta-label">Cron</span><span className="meta-value code">{sch.cron_expression}</span></div>}
                <div className="schedule-meta"><span className="meta-label">Runs</span><span className="meta-value">{sch.run_count}/{sch.max_runs || '∞'}</span></div>
                <div className="schedule-meta"><span className="meta-label">Last Run</span><span className="meta-value">{formatTime(sch.last_run_at)}</span></div>
                <div className="schedule-meta"><span className="meta-label">Next Run</span><span className="meta-value">{formatTime(sch.next_run_at)}</span></div>
              </div>
              <p className="schedule-prompt">{sch.prompt}</p>
              <div className="schedule-card-actions">
                {sch.status === 'active' && <button className="btn-secondary-sm" onClick={() => handlePause(sch.id)}>⏸ Pause</button>}
                {sch.status === 'paused' && <button className="btn-secondary-sm" onClick={() => handleResume(sch.id)}>▶ Resume</button>}
                <button className="btn-danger-sm" onClick={() => handleDelete(sch.id)}>Cancel</button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="panel-empty">
          <span className="empty-icon">🕐</span>
          <p>No scheduled tasks yet</p>
          <p className="empty-hint">Create a schedule to run tasks automatically on cron or interval triggers.</p>
        </div>
      )}

      <style>{styles}</style>
    </div>
  );
};

const styles = `
.panel-container { padding: 24px; max-width: 1200px; margin: 0 auto; }
.panel-header h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; color: var(--text, #1f2937); }
.panel-subtitle { color: var(--text-secondary, #6b7280); margin-bottom: 24px; font-size: 0.9rem; }
.panel-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 0; color: var(--text-secondary, #9ca3af); gap: 16px; font-size: 0.95rem; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--border, #e5e7eb); border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-banner { background: #fef2f2; color: #991b1b; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; }
.panel-empty { text-align: center; padding: 60px 0; color: var(--text-secondary, #9ca3af); }
.empty-icon { font-size: 3rem; display: block; margin-bottom: 12px; }
.panel-empty p { font-size: 0.95rem; margin-bottom: 6px; }
.empty-hint { font-size: 0.8rem; color: var(--text-secondary, #9ca3af); max-width: 400px; margin: 0 auto; line-height: 1.5; }

.stats-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-item { flex: 1; min-width: 140px; background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 14px 18px; display: flex; align-items: center; gap: 12px; }
.stat-icon { font-size: 1.5rem; }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: 1.3rem; font-weight: 800; color: var(--text, #1f2937); }
.stat-label { font-size: 0.72rem; color: var(--text-secondary, #6b7280); font-weight: 600; }

.action-bar { display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; }
.btn-primary-sm { padding: 8px 16px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-primary-sm:hover { background: #2563eb; }
.btn-secondary-sm { padding: 8px 16px; background: var(--bg-card, #fff); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-secondary-sm:hover { border-color: #3b82f6; color: #3b82f6; }
.btn-danger-sm { padding: 6px 12px; background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.8rem; }
.btn-danger-sm:hover { background: #fee2e2; }

.schedule-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 16px; }
.schedule-card { background: var(--bg-card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 20px; transition: box-shadow 0.2s; }
.schedule-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.schedule-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--border, #f3f4f6); }
.schedule-name { font-weight: 700; font-size: 0.95rem; color: var(--text, #1f2937); }
.schedule-status { font-size: 0.8rem; font-weight: 700; text-transform: capitalize; }
.schedule-detail { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.schedule-meta { display: flex; justify-content: space-between; align-items: center; }
.meta-label { font-size: 0.8rem; color: var(--text-secondary, #6b7280); }
.meta-value { font-size: 0.8rem; font-weight: 600; color: var(--text, #374151); }
.meta-value.code { font-family: monospace; font-size: 0.75rem; background: var(--bg-card, #f3f4f6); padding: 2px 6px; border-radius: 4px; }
.schedule-prompt { font-size: 0.82rem; color: var(--text-secondary, #4b5563); margin-bottom: 14px; line-height: 1.4; max-height: 60px; overflow: hidden; text-overflow: ellipsis; }
.schedule-card-actions { display: flex; gap: 8px; }

.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text, #374151); }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-size: 0.9rem; background: var(--bg-card, #fff); color: var(--text, #1f2937); font-family: inherit; }
.form-group textarea { resize: vertical; }

.exec-result { margin-top: 12px; padding: 12px; background: var(--bg-card, #1f2937); color: #e5e7eb; border-radius: 8px; font-size: 0.8rem; overflow-x: auto; max-height: 200px; overflow-y: auto; white-space: pre-wrap; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--bg-card, #fff); border-radius: 16px; padding: 28px; width: 90%; max-width: 520px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal h3 { font-size: 1.15rem; font-weight: 700; margin-bottom: 20px; color: var(--text, #1f2937); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.btn-primary { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { padding: 10px 20px; background: var(--bg-card, #f3f4f6); color: var(--text, #374151); border: 1px solid var(--border, #d1d5db); border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
`;

export default SchedulerPanel;