import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface PresenceStats {
  total_agents: number;
  online_count: number;
  offline_count: number;
  busy_count: number;
  away_count: number;
}

interface AgentProfile {
  agent_id: string;
  name: string;
  role: string;
  avatar_url: string;
  status: string;
  last_seen: string;
  created_at: string;
}

interface PresenceState {
  agent_id: string;
  name: string;
  status: string;
  current_activity: string;
  online_since: string | null;
  last_heartbeat: string;
  metadata: Record<string, string>;
}

interface TimelineEntry {
  timestamp: string;
  event: string;
  status: string;
  activity: string;
  details: string;
}

interface ScheduleEntry {
  day: string;
  start_time: string;
  end_time: string;
  available: boolean;
  label: string;
}

interface SessionContext {
  context_id: string;
  agent_id: string;
  name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

interface PresenceEvent {
  event_id: string;
  agent_id: string;
  event_type: string;
  status: string;
  message: string;
  timestamp: string;
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

export const PresenceEnginePanel: React.FC = () => {
  const toast = useToast();

  // ── State ──
  const [stats, setStats] = useState<PresenceStats | null>(null);
  const [profiles, setProfiles] = useState<AgentProfile[]>([]);
  const [presenceState, setPresenceState] = useState<PresenceState | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [schedule, setSchedule] = useState<ScheduleEntry[]>([]);
  const [contexts, setContexts] = useState<SessionContext[]>([]);
  const [events, setEvents] = useState<PresenceEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<
    'overview' | 'profiles' | 'state' | 'timeline' | 'schedule' | 'context' | 'events'
  >('overview');

  // Presence state form
  const [statusForm, setStatusForm] = useState({
    agent_id: '',
    status: 'online',
    activity: '',
  });
  const [settingStatus, setSettingStatus] = useState(false);

  // Timeline agent selector
  const [timelineAgentId, setTimelineAgentId] = useState('');
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Schedule form
  const [scheduleForm, setScheduleForm] = useState({
    day: 'monday',
    start_time: '09:00',
    end_time: '17:00',
    available: true,
    label: '',
  });
  const [savingSchedule, setSavingSchedule] = useState(false);

  // Context form
  const [contextForm, setContextForm] = useState({
    agent_id: '',
    name: '',
    content: '',
  });
  const [savingContext, setSavingContext] = useState(false);

  // ── Data Loading ──

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, pr, ps, sch, ctx, ev] = await Promise.all([
        request<PresenceStats>('/presence/stats').catch(() => null),
        request<AgentProfile[]>('/presence/profiles').catch(() => []),
        request<PresenceState>('/presence').catch(() => null),
        request<ScheduleEntry[]>('/presence/schedule').catch(() => []),
        request<SessionContext[]>('/presence/context').catch(() => []),
        request<PresenceEvent[]>('/presence/events').catch(() => []),
      ]);
      setStats(s);
      setProfiles(Array.isArray(pr) ? pr : (pr as any)?.profiles || []);
      setPresenceState(ps);
      setSchedule(Array.isArray(sch) ? sch : (sch as any)?.schedule || []);
      setContexts(Array.isArray(ctx) ? ctx : (ctx as any)?.contexts || []);
      setEvents(Array.isArray(ev) ? ev : (ev as any)?.events || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load presence engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Handlers ──

  const handleSetPresence = async () => {
    if (!statusForm.agent_id) return;
    try {
      setSettingStatus(true);
      await request('/presence/set', {
        method: 'POST',
        body: JSON.stringify({
          agent_id: statusForm.agent_id,
          status: statusForm.status,
          activity: statusForm.activity || undefined,
        }),
      });
      toast.success(`Presence set to "${statusForm.status}" for ${statusForm.agent_id}`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSettingStatus(false);
    }
  };

  const handleLoadTimeline = async () => {
    if (!timelineAgentId.trim()) return;
    try {
      setTimelineLoading(true);
      const data = await request<TimelineEntry[]>(`/presence/${encodeURIComponent(timelineAgentId)}/timeline`);
      setTimeline(Array.isArray(data) ? data : (data as any)?.timeline || []);
      toast.success(`Loaded timeline for ${timelineAgentId}`);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleSaveSchedule = async () => {
    try {
      setSavingSchedule(true);
      await request('/presence/schedule', {
        method: 'POST',
        body: JSON.stringify(scheduleForm),
      });
      toast.success('Schedule entry saved');
      setScheduleForm({ day: 'monday', start_time: '09:00', end_time: '17:00', available: true, label: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSavingSchedule(false);
    }
  };

  const handleSaveContext = async () => {
    if (!contextForm.agent_id || !contextForm.name.trim() || !contextForm.content.trim()) return;
    try {
      setSavingContext(true);
      await request('/presence/context', {
        method: 'POST',
        body: JSON.stringify(contextForm),
      });
      toast.success(`Context "${contextForm.name}" saved`);
      setContextForm({ agent_id: '', name: '', content: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSavingContext(false);
    }
  };

  const handleLoadContext = async (contextId: string) => {
    try {
      const ctx = await request<SessionContext>(`/presence/context/${contextId}`);
      toast.info(`Loaded context: ${ctx.name}`);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // ── Helpers ──

  const statusColors: Record<string, string> = {
    online: '#22c55e',
    offline: '#9ca3af',
    busy: '#ef4444',
    away: '#f59e0b',
    idle: '#3b82f6',
  };

  const eventTypeColors: Record<string, string> = {
    status_change: '#4f6ef7',
    heartbeat: '#22c55e',
    activity_update: '#8b5cf6',
    error: '#ef4444',
    connection: '#06b6d4',
    disconnection: '#9ca3af',
  };

  const dayLabels: Record<string, string> = {
    monday: 'Monday',
    tuesday: 'Tuesday',
    wednesday: 'Wednesday',
    thursday: 'Thursday',
    friday: 'Friday',
    saturday: 'Saturday',
    sunday: 'Sunday',
  };

  // ── Loading State ──

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Presence Engine</h2>
          <p className="panel-subtitle">Agent presence, availability, and session continuity management</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading presence engine data...</span>
        </div>
      </div>
    );
  }

  // ── Main Render ──

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Presence Engine</h2>
        <p className="panel-subtitle">Agent presence tracking, availability scheduling, and session continuity</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_agents}</span>
              <span className="stat-label">Total Agents</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.online_count}</span>
              <span className="stat-label">Online</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#9ca3af' }}>{stats.offline_count}</span>
              <span className="stat-label">Offline</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#ef4444' }}>{stats.busy_count}</span>
              <span className="stat-label">Busy</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>{stats.away_count}</span>
              <span className="stat-label">Away</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'profiles', 'state', 'timeline', 'schedule', 'context', 'events'] as const).map((s) => (
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
              <h3>Presence Overview</h3>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
                <div style={{ flex: '1 0 180px', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
                  <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>Online Rate</h4>
                  <strong style={{ fontSize: '1.5rem', color: '#22c55e' }}>
                    {stats.total_agents > 0
                      ? ((stats.online_count / stats.total_agents) * 100).toFixed(1)
                      : 0}%
                  </strong>
                  <span style={{ marginLeft: 8, color: '#6b7280' }}>of agents online</span>
                </div>
                <div style={{ flex: '1 0 180px', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
                  <h4 style={{ margin: '0 0 8px 0', color: '#374151' }}>Busy Rate</h4>
                  <strong style={{ fontSize: '1.5rem', color: '#ef4444' }}>
                    {stats.total_agents > 0
                      ? ((stats.busy_count / stats.total_agents) * 100).toFixed(1)
                      : 0}%
                  </strong>
                  <span style={{ marginLeft: 8, color: '#6b7280' }}>currently busy</span>
                </div>
              </div>

              <div className="dashboard-stat-row">
                <span>Total Agents</span>
                <strong>{stats.total_agents}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Online</span>
                <strong style={{ color: '#22c55e' }}>{stats.online_count}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Offline</span>
                <strong style={{ color: '#9ca3af' }}>{stats.offline_count}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Busy</span>
                <strong style={{ color: '#ef4444' }}>{stats.busy_count}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Away</span>
                <strong style={{ color: '#f59e0b' }}>{stats.away_count}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Schedules Configured</span>
                <strong style={{ color: '#8b5cf6' }}>{schedule.length}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Session Contexts</span>
                <strong style={{ color: '#4f6ef7' }}>{contexts.length}</strong>
              </div>

              {/* Current Presence State */}
              {presenceState && (
                <>
                  <h3 style={{ marginTop: 24 }}>Current Presence</h3>
                  <div
                    style={{
                      padding: 16,
                      background: '#f8fafc',
                      borderRadius: 8,
                    }}
                  >
                    <div className="dashboard-stat-row">
                      <span>Agent</span>
                      <strong>{presenceState.name}</strong>
                    </div>
                    <div className="dashboard-stat-row">
                      <span>Status</span>
                      <strong style={{ color: statusColors[presenceState.status] || '#9ca3af' }}>
                        {presenceState.status}
                      </strong>
                    </div>
                    <div className="dashboard-stat-row">
                      <span>Activity</span>
                      <strong>{presenceState.current_activity || 'None'}</strong>
                    </div>
                    {presenceState.online_since && (
                      <div className="dashboard-stat-row">
                        <span>Online Since</span>
                        <strong>{new Date(presenceState.online_since).toLocaleString()}</strong>
                      </div>
                    )}
                    <div className="dashboard-stat-row">
                      <span>Last Heartbeat</span>
                      <strong>{new Date(presenceState.last_heartbeat).toLocaleString()}</strong>
                    </div>
                  </div>
                </>
              )}

              {/* Recent Events */}
              <h3 style={{ marginTop: 24 }}>Recent Events</h3>
              {events.length === 0 ? (
                <div className="panel-empty">No presence events recorded</div>
              ) : (
                <div className="forge-skill-list">
                  {events.slice(0, 5).map((evt) => (
                    <div key={evt.event_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ fontSize: '0.9rem' }}>
                          {evt.message}
                        </div>
                        <span
                          className="dashboard-badge"
                          style={{
                            background: eventTypeColors[evt.event_type] || '#9ca3af',
                            color: '#fff',
                          }}
                        >
                          {evt.event_type}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>
                          Agent: {evt.agent_id} | Status:{' '}
                          <span style={{ color: statusColors[evt.status] || '#9ca3af', fontWeight: 600 }}>
                            {evt.status}
                          </span>
                        </div>
                        <div>{new Date(evt.timestamp).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Profiles Section ── */}
      {activeSection === 'profiles' && (
        <div className="dashboard-section">
          <h3>Agent Profiles ({profiles.length})</h3>

          {profiles.length === 0 ? (
            <div className="panel-empty">No agent profiles found</div>
          ) : (
            <div className="forge-skill-list">
              {profiles.map((profile) => (
                <div key={profile.agent_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">
                      {profile.avatar_url && (
                        <span style={{ marginRight: 8, fontSize: '1.2rem' }}>{profile.avatar_url}</span>
                      )}
                      {profile.name}
                    </div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: statusColors[profile.status] || '#9ca3af',
                        color: '#fff',
                      }}
                    >
                      {profile.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Role: {profile.role}</div>
                    <div>Last Seen: {new Date(profile.last_seen).toLocaleString()}</div>
                    <div>Created: {new Date(profile.created_at).toLocaleString()}</div>
                    <div style={{ marginTop: 4, fontSize: '0.8rem', color: '#9ca3af', fontFamily: 'monospace' }}>
                      ID: {profile.agent_id}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── State Section ── */}
      {activeSection === 'state' && (
        <div className="dashboard-section">
          <h3>Presence State Management</h3>

          {/* Set Presence Form */}
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <h4>Set Agent Presence</h4>
            <div className="form-group">
              <label>Agent</label>
              <select
                value={statusForm.agent_id}
                onChange={(e) => setStatusForm((f) => ({ ...f, agent_id: e.target.value }))}
              >
                <option value="">Select an agent...</option>
                {profiles.map((p) => (
                  <option key={p.agent_id} value={p.agent_id}>
                    {p.name} ({p.role})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Status</label>
                <select
                  value={statusForm.status}
                  onChange={(e) => setStatusForm((f) => ({ ...f, status: e.target.value }))}
                >
                  <option value="online">Online</option>
                  <option value="offline">Offline</option>
                  <option value="busy">Busy</option>
                  <option value="away">Away</option>
                  <option value="idle">Idle</option>
                </select>
              </div>
              <div className="form-group">
                <label>Activity</label>
                <input
                  type="text"
                  value={statusForm.activity}
                  onChange={(e) => setStatusForm((f) => ({ ...f, activity: e.target.value }))}
                  placeholder="e.g., Working on code review"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleSetPresence}
              disabled={settingStatus || !statusForm.agent_id}
              style={{ background: '#4f6ef7' }}
            >
              {settingStatus ? 'Setting...' : 'Set Presence'}
            </button>
          </div>

          {/* Current State Display */}
          {presenceState && (
            <div
              style={{
                padding: 16,
                background: '#f8fafc',
                borderRadius: 8,
                marginTop: 16,
              }}
            >
              <h4 style={{ margin: '0 0 12px 0', color: '#374151' }}>Current State</h4>
              <div className="dashboard-stat-row">
                <span>Agent</span>
                <strong>{presenceState.name}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Status</span>
                <strong style={{ color: statusColors[presenceState.status] || '#9ca3af' }}>
                  {presenceState.status}
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Activity</span>
                <strong>{presenceState.current_activity || 'None'}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Last Heartbeat</span>
                <strong>{new Date(presenceState.last_heartbeat).toLocaleString()}</strong>
              </div>
              {presenceState.online_since && (
                <div className="dashboard-stat-row">
                  <span>Online Since</span>
                  <strong>{new Date(presenceState.online_since).toLocaleString()}</strong>
                </div>
              )}
              {presenceState.metadata && Object.keys(presenceState.metadata).length > 0 && (
                <>
                  <h4 style={{ margin: '12px 0 8px 0', color: '#374151' }}>Metadata</h4>
                  {Object.entries(presenceState.metadata).map(([key, value]) => (
                    <div key={key} className="dashboard-stat-row">
                      <span>{key}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Timeline Section ── */}
      {activeSection === 'timeline' && (
        <div className="dashboard-section">
          <h3>Activity Timeline</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'flex-end' }}>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label>Agent ID</label>
              <input
                type="text"
                value={timelineAgentId}
                onChange={(e) => setTimelineAgentId(e.target.value)}
                placeholder="Enter agent ID to view timeline..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleLoadTimeline}
              disabled={timelineLoading || !timelineAgentId.trim()}
              style={{ background: '#8b5cf6', height: 38 }}
            >
              {timelineLoading ? 'Loading...' : 'Load Timeline'}
            </button>
          </div>

          {timeline.length === 0 ? (
            <div className="panel-empty">
              {timelineAgentId
                ? `No timeline entries found for agent "${timelineAgentId}"`
                : 'Enter an agent ID and click "Load Timeline" to view activity'}
            </div>
          ) : (
            <div className="forge-skill-list">
              {timeline.map((entry, idx) => (
                <div key={idx} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.9rem' }}>
                      {entry.activity}
                    </div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: statusColors[entry.status] || '#3b82f6',
                        color: '#fff',
                      }}
                    >
                      {entry.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Event: {entry.event}</div>
                    {entry.details && <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{entry.details}</div>}
                    <div>{new Date(entry.timestamp).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Schedule Section ── */}
      {activeSection === 'schedule' && (
        <div className="dashboard-section">
          <h3>Availability Schedule</h3>

          {/* Schedule Form */}
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <h4>Add Schedule Entry</h4>
            <div className="form-row">
              <div className="form-group">
                <label>Day</label>
                <select
                  value={scheduleForm.day}
                  onChange={(e) => setScheduleForm((f) => ({ ...f, day: e.target.value }))}
                >
                  {Object.entries(dayLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Available</label>
                <select
                  value={scheduleForm.available ? 'true' : 'false'}
                  onChange={(e) =>
                    setScheduleForm((f) => ({ ...f, available: e.target.value === 'true' }))
                  }
                >
                  <option value="true">Available</option>
                  <option value="false">Unavailable</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Start Time</label>
                <input
                  type="time"
                  value={scheduleForm.start_time}
                  onChange={(e) => setScheduleForm((f) => ({ ...f, start_time: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>End Time</label>
                <input
                  type="time"
                  value={scheduleForm.end_time}
                  onChange={(e) => setScheduleForm((f) => ({ ...f, end_time: e.target.value }))}
                />
              </div>
            </div>
            <div className="form-group">
              <label>Label</label>
              <input
                type="text"
                value={scheduleForm.label}
                onChange={(e) => setScheduleForm((f) => ({ ...f, label: e.target.value }))}
                placeholder="e.g., Core working hours"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleSaveSchedule}
              disabled={savingSchedule}
              style={{ background: '#22c55e' }}
            >
              {savingSchedule ? 'Saving...' : 'Save Schedule Entry'}
            </button>
          </div>

          {/* Current Schedule */}
          <h4>Current Schedule ({schedule.length})</h4>
          {schedule.length === 0 ? (
            <div className="panel-empty">No schedule entries configured</div>
          ) : (
            <div className="forge-skill-list">
              {schedule.map((entry, idx) => (
                <div key={idx} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">
                      {dayLabels[entry.day] || entry.day}
                      {entry.label && ` - ${entry.label}`}
                    </div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: entry.available ? '#22c55e' : '#9ca3af',
                        color: '#fff',
                      }}
                    >
                      {entry.available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      {entry.start_time} - {entry.end_time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Context Section ── */}
      {activeSection === 'context' && (
        <div className="dashboard-section">
          <h3>Session Context</h3>

          {/* Save Context Form */}
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <h4>Save Continuity Prompt</h4>
            <div className="form-group">
              <label>Agent</label>
              <select
                value={contextForm.agent_id}
                onChange={(e) => setContextForm((f) => ({ ...f, agent_id: e.target.value }))}
              >
                <option value="">Select an agent...</option>
                {profiles.map((p) => (
                  <option key={p.agent_id} value={p.agent_id}>
                    {p.name} ({p.role})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Context Name</label>
              <input
                type="text"
                value={contextForm.name}
                onChange={(e) => setContextForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g., Project Alpha Session"
              />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={4}
                value={contextForm.content}
                onChange={(e) => setContextForm((f) => ({ ...f, content: e.target.value }))}
                placeholder="Enter the continuity prompt or session context..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleSaveContext}
              disabled={savingContext || !contextForm.agent_id || !contextForm.name.trim() || !contextForm.content.trim()}
              style={{ background: '#4f6ef7' }}
            >
              {savingContext ? 'Saving...' : 'Save Context'}
            </button>
          </div>

          {/* Saved Contexts */}
          <h4>Saved Contexts ({contexts.length})</h4>
          {contexts.length === 0 ? (
            <div className="panel-empty">No session contexts saved</div>
          ) : (
            <div className="forge-skill-list">
              {contexts.map((ctx) => (
                <div key={ctx.context_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{ctx.name}</div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: '#4f6ef7',
                        color: '#fff',
                      }}
                    >
                      {ctx.agent_id}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div
                      style={{
                        color: '#475569',
                        fontSize: '0.85rem',
                        maxHeight: 60,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {ctx.content}
                    </div>
                    <div style={{ marginTop: 4 }}>
                      Created: {new Date(ctx.created_at).toLocaleString()}
                    </div>
                    <div>Updated: {new Date(ctx.updated_at).toLocaleString()}</div>
                    <div style={{ marginTop: 8 }}>
                      <button
                        className="btn-sm"
                        style={{ background: '#8b5cf6', color: '#fff', border: 'none' }}
                        onClick={() => handleLoadContext(ctx.context_id)}
                      >
                        Load
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Events Section ── */}
      {activeSection === 'events' && (
        <div className="dashboard-section">
          <h3>Presence Events Feed ({events.length})</h3>

          {events.length === 0 ? (
            <div className="panel-empty">No presence events recorded</div>
          ) : (
            <div className="forge-skill-list">
              {events.map((evt) => (
                <div key={evt.event_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.9rem' }}>
                      {evt.message}
                    </div>
                    <span
                      className="dashboard-badge"
                      style={{
                        background: eventTypeColors[evt.event_type] || '#9ca3af',
                        color: '#fff',
                      }}
                    >
                      {evt.event_type}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      Agent:{' '}
                      <span style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{evt.agent_id}</span>
                      {' '}| Status:{' '}
                      <span style={{ color: statusColors[evt.status] || '#9ca3af', fontWeight: 600 }}>
                        {evt.status}
                      </span>
                    </div>
                    <div>{new Date(evt.timestamp).toLocaleString()}</div>
                    <div style={{ fontSize: '0.8rem', color: '#9ca3af', fontFamily: 'monospace', marginTop: 2 }}>
                      ID: {evt.event_id}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PresenceEnginePanel;