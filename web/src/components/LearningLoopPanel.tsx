import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#ea580c',
  secondary: '#fb923c',
  bg: '#fff7ed',
  border: '#fdba74',
  accent: '#ffedd5',
  text: '#9a3412',
};

const FEEDBACK_TYPES = ['explicit', 'implicit', 'corrective', 'reinforcement', 'preference'];
const LEARNING_SIGNALS = ['positive', 'negative', 'neutral', 'correction', 'adaptation'];

export const LearningLoopPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'record' | 'events'>('overview');

  const [recordForm, setRecordForm] = useState({
    feedback_type: 'implicit', signal: 'neutral', description: '', tags: '',
  });
  const [sessionId, setSessionId] = useState<string>('');
  const [recording, setRecording] = useState(false);
  const [events, setEvents] = useState<any[] | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.learningLoop.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load learning loop data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateSession = async () => {
    try {
      const result = await api.learningLoop.createSession({ user_id: 'default' });
      setSessionId(result.session_id);
      toast.success(`Session created: ${result.session_id}`);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordEvent = async () => {
    if (!sessionId) {
      toast.warning('Create a session first');
      return;
    }
    try {
      setRecording(true);
      await api.learningLoop.recordEvent({
        session_id: sessionId,
        feedback_type: recordForm.feedback_type,
        signal: recordForm.signal,
        description: recordForm.description || undefined,
        tags: recordForm.tags ? recordForm.tags.split(',').map(s => s.trim()) : undefined,
      });
      toast.success('Event recorded');
      setRecordForm({ feedback_type: 'implicit', signal: 'neutral', description: '', tags: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
    finally { setRecording(false); }
  };

  const handleLoadEvents = async () => {
    try {
      const r = await api.learningLoop.events(20);
      setEvents(r.events || r);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔄 Interactive Learning Loop</h2>
          <p className="panel-subtitle">Continuous learning and adaptation system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading learning loop...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔄 Interactive Learning Loop</h2>
        <p className="panel-subtitle">Continuous learning and adaptation system</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_events ?? '-'}</span><span className="stat-label">Total Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_adaptations ?? '-'}</span><span className="stat-label">Adaptations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.active_rules ?? '-'}</span><span className="stat-label">Active Rules</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.user_profiles ?? '-'}</span><span className="stat-label">User Profiles</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'record', 'events'] as const).map(s => (
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

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Learning Loop Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.active_sessions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Rule Confidence</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_rule_confidence?.toFixed?.(2) ?? '-'}</div>
              </div>
            </div>
          </div>
          {stats.signal_distribution && Object.keys(stats.signal_distribution).length > 0 && (
            <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8 }}>
              <h4 style={{ color: themeColors.text }}>Signal Distribution</h4>
              {Object.entries(stats.signal_distribution).map(([signal, count]: [string, any]) => (
                <div key={signal} className="dashboard-stat-row">
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{signal}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
          {stats.rules_by_type && Object.keys(stats.rules_by_type).length > 0 && (
            <div style={{ padding: 16, background: themeColors.accent, borderRadius: 8, marginTop: 12 }}>
              <h4 style={{ color: themeColors.text }}>Rules by Type</h4>
              {Object.entries(stats.rules_by_type).map(([type, count]: [string, any]) => (
                <div key={type} className="dashboard-stat-row">
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{type.replace(/_/g, ' ')}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Record Event */}
      {activeSection === 'record' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Record Learning Event</h3>
          <div style={{ marginBottom: 16 }}>
            {sessionId ? (
              <div style={{ padding: '8px 12px', background: themeColors.accent, borderRadius: 6, marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: themeColors.text, fontSize: '0.85rem' }}>Session: <strong>{sessionId}</strong></span>
                <button className="btn-sm" onClick={() => setSessionId('')}>Clear</button>
              </div>
            ) : (
              <button className="btn-primary" style={{ background: themeColors.secondary }} onClick={handleCreateSession}>
                Create Session
              </button>
            )}
          </div>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Feedback Type</label>
                <select value={recordForm.feedback_type} onChange={e => setRecordForm(f => ({ ...f, feedback_type: e.target.value }))}>
                  {FEEDBACK_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Signal</label>
                <select value={recordForm.signal} onChange={e => setRecordForm(f => ({ ...f, signal: e.target.value }))}>
                  {LEARNING_SIGNALS.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={recordForm.description}
                onChange={e => setRecordForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the learning event..."
              />
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                value={recordForm.tags}
                onChange={e => setRecordForm(f => ({ ...f, tags: e.target.value }))}
                placeholder="learning, feedback, adaptation"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRecordEvent}
              disabled={recording || !sessionId}
            >
              {recording ? 'Recording...' : '📝 Record Event'}
            </button>
          </div>
        </div>
      )}

      {/* Events */}
      {activeSection === 'events' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Events</h3>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleLoadEvents}>Load Events</button>
          </div>
          {events ? (
            events.length === 0 ? (
              <div className="panel-empty">No learning events yet</div>
            ) : (
              <div className="forge-skill-list">
                {events.map((e: any, idx: number) => (
                  <div key={e.event_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                    <div className="forge-skill-header">
                      <div className="forge-skill-name" style={{ color: themeColors.text }}>{e.description || e.feedback_type}</div>
                      <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                        {e.signal || e.feedback_type}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      <div>Type: {e.feedback_type} | Signal: {e.signal}</div>
                      {e.tags?.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          {e.tags.map((tag: string) => (
                            <span key={tag} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="panel-empty">Click "Load Events" to view recent learning events</div>
          )}
        </div>
      )}
    </div>
  );
};

export default LearningLoopPanel;