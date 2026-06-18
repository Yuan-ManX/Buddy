import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

interface AutomationStats {
  registry: { total: number; by_type: Record<string, number>; by_state: Record<string, number> };
  scheduler: { scheduled: number; active: number; next_run: string | null };
  runner: { total_executions: number; successful: number; failed: number; success_rate: number };
  watcher: { events_watched: number; triggers_fired: number };
  analytics: { total_automations: number; total_executions: number; avg_success_rate: number };
}

interface AutomationItem {
  automation_id: string;
  name: string;
  automation_type: string;
  state: string;
}

export const AutomationPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<AutomationStats | null>(null);
  const [automations, setAutomations] = useState<AutomationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'register' | 'trigger' | 'list'>('overview');

  // Register form
  const [registerForm, setRegisterForm] = useState({
    name: '',
    automation_type: 'scheduled',
    trigger_type: 'cron',
    trigger_config: '',
    action_template: '',
    created_by: '',
  });

  // Trigger form
  const [triggerForm, setTriggerForm] = useState({
    event_type: '',
    source: '',
    payload: '',
  });
  const [triggerResult, setTriggerResult] = useState<any>(null);

  // Execute
  const [executeId, setExecuteId] = useState('');
  const [executeResult, setExecuteResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsRes, listRes] = await Promise.all([
        fetch('/api/automation/stats'),
        fetch('/api/automation/list'),
      ]);
      const s = await statsRes.json();
      const l = await listRes.json();
      setStats(s);
      setAutomations(l.automations || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRegister = async () => {
    try {
      let triggerConfig = {};
      try {
        triggerConfig = JSON.parse(registerForm.trigger_config || '{}');
      } catch {}
      const res = await fetch('/api/automation/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...registerForm,
          trigger_config: triggerConfig,
        }),
      });
      const data = await res.json();
      toast?.success?.('Registered: ' + data.automation_id);
      setRegisterForm({ name: '', automation_type: 'scheduled', trigger_type: 'cron', trigger_config: '', action_template: '', created_by: '' });
      loadData();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleTrigger = async () => {
    try {
      let payload = {};
      try {
        payload = JSON.parse(triggerForm.payload || '{}');
      } catch {}
      const res = await fetch('/api/automation/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: triggerForm.event_type,
          source: triggerForm.source,
          payload,
        }),
      });
      const data = await res.json();
      setTriggerResult(data);
      loadData();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleExecute = async () => {
    try {
      const res = await fetch(`/api/automation/${executeId}/execute`, { method: 'POST' });
      const data = await res.json();
      setExecuteResult(data);
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  if (loading) return <div className="panel loading">Loading automation core...</div>;

  return (
    <div className="panel automation-panel">
      <div className="panel-header">
        <h2>Automation Core</h2>
        <span className="panel-badge">
          {stats ? `${stats.registry?.total || 0} automations` : 'Loading'}
        </span>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-tabs">
        {(['overview', 'register', 'trigger', 'list'] as const).map((s) => (
          <button
            key={s}
            className={`panel-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="panel-content">
        {activeSection === 'overview' && stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.registry?.total || 0}</div>
              <div className="stat-label">Registered</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.scheduler?.active || 0}</div>
              <div className="stat-label">Active</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.runner?.total_executions || 0}</div>
              <div className="stat-label">Executions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{(stats.runner?.success_rate || 0).toFixed(1)}%</div>
              <div className="stat-label">Success Rate</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.watcher?.events_watched || 0}</div>
              <div className="stat-label">Events Watched</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.watcher?.triggers_fired || 0}</div>
              <div className="stat-label">Triggers Fired</div>
            </div>

            {stats.registry?.by_type && (
              <div className="section-card full-width">
                <h3>By Type</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.registry.by_type).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.registry.by_type).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.registry?.by_state && (
              <div className="section-card full-width">
                <h3>By State</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.registry.by_state).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.registry.by_state).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'register' && (
          <div className="form-section">
            <h3>Register Automation</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Name</label>
                <input type="text" value={registerForm.name} onChange={e => setRegisterForm({ ...registerForm, name: e.target.value })} placeholder="My Automation" />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={registerForm.automation_type} onChange={e => setRegisterForm({ ...registerForm, automation_type: e.target.value })}>
                  <option value="scheduled">Scheduled</option>
                  <option value="event_driven">Event Driven</option>
                  <option value="pipeline">Pipeline</option>
                  <option value="reactive">Reactive</option>
                </select>
              </div>
              <div className="form-group">
                <label>Trigger Type</label>
                <select value={registerForm.trigger_type} onChange={e => setRegisterForm({ ...registerForm, trigger_type: e.target.value })}>
                  <option value="cron">Cron</option>
                  <option value="event">Event</option>
                  <option value="webhook">Webhook</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
              <div className="form-group">
                <label>Created By</label>
                <input type="text" value={registerForm.created_by} onChange={e => setRegisterForm({ ...registerForm, created_by: e.target.value })} placeholder="agent-..." />
              </div>
              <div className="form-group full-width">
                <label>Trigger Config (JSON)</label>
                <textarea value={registerForm.trigger_config} onChange={e => setRegisterForm({ ...registerForm, trigger_config: e.target.value })} placeholder='{"cron": "0 * * * *"}' rows={2} />
              </div>
              <div className="form-group full-width">
                <label>Action Template</label>
                <textarea value={registerForm.action_template} onChange={e => setRegisterForm({ ...registerForm, action_template: e.target.value })} placeholder="Describe what to do when triggered..." rows={3} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleRegister}>Register</button>
          </div>
        )}

        {activeSection === 'trigger' && (
          <div className="form-section">
            <h3>Trigger Event</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Event Type</label>
                <input type="text" value={triggerForm.event_type} onChange={e => setTriggerForm({ ...triggerForm, event_type: e.target.value })} placeholder="task_completed" />
              </div>
              <div className="form-group">
                <label>Source</label>
                <input type="text" value={triggerForm.source} onChange={e => setTriggerForm({ ...triggerForm, source: e.target.value })} placeholder="agent-..." />
              </div>
              <div className="form-group full-width">
                <label>Payload (JSON)</label>
                <textarea value={triggerForm.payload} onChange={e => setTriggerForm({ ...triggerForm, payload: e.target.value })} placeholder='{"key": "value"}' rows={3} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleTrigger}>Trigger</button>
            {triggerResult && (
              <div className="result-card">
                <pre>{JSON.stringify(triggerResult, null, 2)}</pre>
              </div>
            )}

            <hr />
            <h3>Execute Specific Automation</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Automation ID</label>
                <input type="text" value={executeId} onChange={e => setExecuteId(e.target.value)} placeholder="auto-..." />
              </div>
            </div>
            <button className="btn-primary" onClick={handleExecute} disabled={!executeId}>Execute</button>
            {executeResult && (
              <div className="result-card">
                <pre>{JSON.stringify(executeResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeSection === 'list' && (
          <div className="section-card">
            <h3>Registered Automations</h3>
            {automations.length === 0 ? (
              <p className="empty-text">No automations registered yet.</p>
            ) : (
              <div className="room-list">
                {automations.map((a) => (
                  <div key={a.automation_id} className="room-card">
                    <div className="room-name">{a.name}</div>
                    <div className="room-meta">
                      <span className="room-type-badge">{a.automation_type}</span>
                      <span className={`room-state-badge ${a.state}`}>{a.state}</span>
                    </div>
                    <div className="room-id">ID: {a.automation_id}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};