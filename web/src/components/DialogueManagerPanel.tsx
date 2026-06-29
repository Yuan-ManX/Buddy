import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#0d9488',
  secondary: '#5eead4',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#115e59',
};

const STRATEGIES = [
  'direct_answer', 'socratic', 'guided_discovery', 'step_by_step',
  'brainstorm', 'devils_advocate', 'reflective', 'proactive',
];

const TURN_TYPES = ['user', 'agent', 'system', 'tool'];

const DIALOGUE_ACTS = [
  'assert', 'inform', 'request', 'question', 'confirm', 'acknowledge',
  'reject', 'promise', 'apologize', 'suggest', 'clarify', 'summarize',
  'probe', 'redirect',
];

export const DialogueManagerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'session' | 'turns' | 'strategy'>('overview');

  // Active sessions list (overview)
  const [activeSessions, setActiveSessions] = useState<any[]>([]);
  // All sessions for selectors
  const [sessions, setSessions] = useState<any[]>([]);

  // Session creation form
  const [sessionForm, setSessionForm] = useState({
    session_id: '', agent_id: '', user_id: '',
    strategy: 'direct_answer', session_goals: '',
  });
  const [sessionDetails, setSessionDetails] = useState<any>(null);

  // Turns section
  const [selectedTurnSession, setSelectedTurnSession] = useState('');
  const [turnForm, setTurnForm] = useState({
    turn_type: 'user', dialogue_act: 'inform', content: '', speaker: '',
  });
  const [turns, setTurns] = useState<any[]>([]);
  const [currentState, setCurrentState] = useState<any>(null);
  const [suggestedAct, setSuggestedAct] = useState<any>(null);

  // Strategy section
  const [selectedStrategySession, setSelectedStrategySession] = useState('');
  const [strategyValue, setStrategyValue] = useState('direct_answer');
  const [topicForm, setTopicForm] = useState({
    name: '', description: '', relevance_score: '',
  });
  const [sessionSummary, setSessionSummary] = useState<any>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.dialogueManager.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load dialogue manager data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadActiveSessions = useCallback(async () => {
    try {
      const result = await api.dialogueManager.listSessions(true);
      const list = Array.isArray(result) ? result : (result?.sessions ?? []);
      setActiveSessions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load active sessions');
    }
  }, [toast]);

  const loadAllSessions = useCallback(async () => {
    try {
      const result = await api.dialogueManager.listSessions();
      const list = Array.isArray(result) ? result : (result?.sessions ?? []);
      setSessions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load sessions');
    }
  }, [toast]);

  useEffect(() => { loadStats(); }, [loadStats]);

  // Load data on section change
  useEffect(() => {
    if (activeSection === 'overview') {
      loadActiveSessions();
    } else if (activeSection === 'turns' || activeSection === 'strategy') {
      loadAllSessions();
    }
  }, [activeSection, loadActiveSessions, loadAllSessions]);

  // Session creation
  const handleCreateSession = async () => {
    if (!sessionForm.session_id.trim()) return;
    try {
      const goals = sessionForm.session_goals
        .split(',').map(s => s.trim()).filter(Boolean);
      const result = await api.dialogueManager.createSession({
        session_id: sessionForm.session_id.trim(),
        agent_id: sessionForm.agent_id.trim() || undefined,
        user_id: sessionForm.user_id.trim() || undefined,
        strategy: sessionForm.strategy,
        session_goals: goals.length > 0 ? goals : undefined,
      });
      setSessionDetails(result);
      toast.success(`Session "${sessionForm.session_id}" created`);
      setSessionForm({
        session_id: '', agent_id: '', user_id: '',
        strategy: 'direct_answer', session_goals: '',
      });
      loadStats();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSelectSession = async (sessionId: string) => {
    if (!sessionId) { setSessionDetails(null); return; }
    try {
      const result = await api.dialogueManager.getSession(sessionId);
      setSessionDetails(result);
    } catch (e: any) { toast.error(e.message); }
  };

  // Turn recording
  const loadTurnsData = useCallback(async (sessionId: string) => {
    if (!sessionId) {
      setTurns([]); setCurrentState(null); setSuggestedAct(null);
      return;
    }
    try {
      const [turnsResult, stateResult] = await Promise.all([
        api.dialogueManager.getTurns(sessionId),
        api.dialogueManager.getState(sessionId).catch(() => null),
      ]);
      const turnsList = Array.isArray(turnsResult) ? turnsResult : (turnsResult?.turns ?? []);
      setTurns(turnsList);
      setCurrentState(stateResult);
      setSuggestedAct(null);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load turns');
    }
  }, [toast]);

  const handleRecordTurn = async () => {
    if (!selectedTurnSession || !turnForm.content.trim()) return;
    try {
      await api.dialogueManager.recordTurn(selectedTurnSession, {
        turn_type: turnForm.turn_type,
        dialogue_act: turnForm.dialogue_act,
        content: turnForm.content.trim(),
        speaker: turnForm.speaker.trim() || undefined,
      });
      toast.success('Turn recorded');
      setTurnForm({ turn_type: 'user', dialogue_act: 'inform', content: '', speaker: '' });
      loadTurnsData(selectedTurnSession);
      loadStats();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSuggestAct = async () => {
    if (!selectedTurnSession) return;
    try {
      const result = await api.dialogueManager.suggestAct(selectedTurnSession);
      setSuggestedAct(result);
      toast.success('Next act suggested');
    } catch (e: any) { toast.error(e.message); }
  };

  // Strategy management
  const loadStrategyData = useCallback(async (sessionId: string) => {
    if (!sessionId) { setSessionSummary(null); return; }
    try {
      const summary = await api.dialogueManager.getSummary(sessionId);
      setSessionSummary(summary);
      if (summary?.strategy) setStrategyValue(summary.strategy);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load summary');
    }
  }, [toast]);

  const handleChangeStrategy = async () => {
    if (!selectedStrategySession) return;
    try {
      await api.dialogueManager.setStrategy(selectedStrategySession, strategyValue);
      toast.success(`Strategy changed to "${strategyValue}"`);
      loadStrategyData(selectedStrategySession);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleIntroduceTopic = async () => {
    if (!selectedStrategySession || !topicForm.name.trim()) return;
    try {
      await api.dialogueManager.introduceTopic(selectedStrategySession, {
        name: topicForm.name.trim(),
        description: topicForm.description.trim() || undefined,
        relevance_score: topicForm.relevance_score ? Number(topicForm.relevance_score) : undefined,
      });
      toast.success(`Topic "${topicForm.name}" introduced`);
      setTopicForm({ name: '', description: '', relevance_score: '' });
      loadStrategyData(selectedStrategySession);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>💬 Dialogue Manager</h2>
          <p className="panel-subtitle">Create sessions, record turns, track state, and suggest acts</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading dialogue manager...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💬 Dialogue Manager</h2>
        <p className="panel-subtitle">Create sessions, record turns, track state, and suggest acts</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_sessions ?? '-'}</span><span className="stat-label">Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_sessions ?? '-'}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_turns ?? '-'}</span><span className="stat-label">Turns</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_engagement != null ? Number(stats.avg_engagement).toFixed(2) : '-'}</span><span className="stat-label">Avg Engagement</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'session', 'turns', 'strategy'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Dialogue Manager Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_sessions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.active_sessions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Turns</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_turns ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Session Length</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_session_length != null ? Number(stats.avg_session_length).toFixed(2) : '-'}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Engagement</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_engagement != null ? Number(stats.avg_engagement).toFixed(2) : '-'}</div>
              </div>
            </div>

            {/* Distributions */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 8 }}>State Distribution</div>
                {stats.state_distribution && Object.keys(stats.state_distribution).length > 0 ? (
                  Object.entries(stats.state_distribution).map(([k, v]: any) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: themeColors.text, padding: '2px 0' }}>
                      <span>{k}</span><span style={{ fontWeight: 600 }}>{v}</span>
                    </div>
                  ))
                ) : <div style={{ fontSize: '0.85rem', color: themeColors.text }}>No data</div>}
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 8 }}>Strategy Distribution</div>
                {stats.strategy_distribution && Object.keys(stats.strategy_distribution).length > 0 ? (
                  Object.entries(stats.strategy_distribution).map(([k, v]: any) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: themeColors.text, padding: '2px 0' }}>
                      <span>{k}</span><span style={{ fontWeight: 600 }}>{v}</span>
                    </div>
                  ))
                ) : <div style={{ fontSize: '0.85rem', color: themeColors.text }}>No data</div>}
              </div>
            </div>
          </div>

          {/* Active Sessions */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Active Sessions</h3>
            {activeSessions.length === 0 ? (
              <div style={{ color: themeColors.text, fontSize: '0.9rem', marginTop: 8 }}>No active sessions</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                {activeSessions.map((s: any) => (
                  <div key={s.session_id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                    <div style={{ fontWeight: 600, color: themeColors.text }}>{s.session_id}</div>
                    <div style={{ fontSize: '0.85rem', color: themeColors.text, opacity: 0.8 }}>
                      strategy: {s.strategy ?? '-'} · state: {s.state ?? '-'} · turns: {s.turn_count ?? s.total_turns ?? 0}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Session */}
      {activeSection === 'session' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Session</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={sessionForm.session_id}
                  onChange={e => setSessionForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="e.g. sess-001"
                />
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input
                  type="text"
                  value={sessionForm.agent_id}
                  onChange={e => setSessionForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="e.g. agent-001"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>User ID</label>
                <input
                  type="text"
                  value={sessionForm.user_id}
                  onChange={e => setSessionForm(f => ({ ...f, user_id: e.target.value }))}
                  placeholder="e.g. user-001"
                />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={sessionForm.strategy} onChange={e => setSessionForm(f => ({ ...f, strategy: e.target.value }))}>
                  {STRATEGIES.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Session Goals (comma-separated)</label>
              <input
                type="text"
                value={sessionForm.session_goals}
                onChange={e => setSessionForm(f => ({ ...f, session_goals: e.target.value }))}
                placeholder="e.g. resolve bug, explain approach"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateSession}
              disabled={!sessionForm.session_id.trim()}
            >
              Create Session
            </button>
          </div>

          {/* Session Details */}
          <div className="form-group">
            <label>Select Session to View</label>
            <select
              value={sessionDetails?.session_id ?? ''}
              onChange={e => handleSelectSession(e.target.value)}
            >
              <option value="">-- None --</option>
              {sessions.map((s: any) => (
                <option key={s.session_id} value={s.session_id}>{s.session_id}</option>
              ))}
            </select>
          </div>

          {sessionDetails && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Session Details</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(sessionDetails, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Turns */}
      {activeSection === 'turns' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Record Turn</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session *</label>
              <select
                value={selectedTurnSession}
                onChange={e => { setSelectedTurnSession(e.target.value); loadTurnsData(e.target.value); }}
              >
                <option value="">-- Select --</option>
                {sessions.map((s: any) => (
                  <option key={s.session_id} value={s.session_id}>{s.session_id}</option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Turn Type</label>
                <select value={turnForm.turn_type} onChange={e => setTurnForm(f => ({ ...f, turn_type: e.target.value }))}>
                  {TURN_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Dialogue Act</label>
                <select value={turnForm.dialogue_act} onChange={e => setTurnForm(f => ({ ...f, dialogue_act: e.target.value }))}>
                  {DIALOGUE_ACTS.map(a => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Speaker</label>
                <input
                  type="text"
                  value={turnForm.speaker}
                  onChange={e => setTurnForm(f => ({ ...f, speaker: e.target.value }))}
                  placeholder="e.g. agent or user"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Content *</label>
              <textarea
                rows={3}
                value={turnForm.content}
                onChange={e => setTurnForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Turn content..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRecordTurn}
              disabled={!selectedTurnSession || !turnForm.content.trim()}
            >
              Record Turn
            </button>
          </div>

          {/* Current State & Suggested Act */}
          {selectedTurnSession && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div style={{ padding: '12px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <h4 style={{ color: themeColors.text, marginBottom: 8 }}>Current State</h4>
                {currentState ? (
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(currentState, null, 2)}</pre>
                ) : <div style={{ fontSize: '0.85rem', color: themeColors.text }}>No state</div>}
              </div>
              <div style={{ padding: '12px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <h4 style={{ color: themeColors.text, margin: 0 }}>Suggested Next Act</h4>
                  <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={handleSuggestAct}>Suggest</button>
                </div>
                {suggestedAct ? (
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(suggestedAct, null, 2)}</pre>
                ) : <div style={{ fontSize: '0.85rem', color: themeColors.text }}>Click "Suggest" to get next act</div>}
              </div>
            </div>
          )}

          {/* Turn History */}
          {selectedTurnSession && (
            <div style={{ padding: '12px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text, marginBottom: 8 }}>Turn History ({turns.length})</h4>
              {turns.length === 0 ? (
                <div style={{ fontSize: '0.85rem', color: themeColors.text }}>No turns recorded</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {turns.map((t: any, i: number) => (
                    <div key={t.turn_id ?? i} style={{ padding: 8, background: '#fff', borderRadius: 4, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontSize: '0.8rem', color: themeColors.text, opacity: 0.8 }}>
                        #{i + 1} · {t.turn_type} · {t.dialogue_act} · {t.speaker ?? '-'}
                      </div>
                      <div style={{ fontSize: '0.9rem', color: themeColors.text }}>{t.content}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Strategy */}
      {activeSection === 'strategy' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Strategy & Topics</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session *</label>
              <select
                value={selectedStrategySession}
                onChange={e => { setSelectedStrategySession(e.target.value); loadStrategyData(e.target.value); }}
              >
                <option value="">-- Select --</option>
                {sessions.map((s: any) => (
                  <option key={s.session_id} value={s.session_id}>{s.session_id}</option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Strategy</label>
                <select value={strategyValue} onChange={e => setStrategyValue(e.target.value)}>
                  {STRATEGIES.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button
                  className="btn-primary"
                  style={{ background: themeColors.primary }}
                  onClick={handleChangeStrategy}
                  disabled={!selectedStrategySession}
                >
                  Change Strategy
                </button>
              </div>
            </div>
          </div>

          {/* Introduce Topic */}
          {selectedStrategySession && (
            <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
              <h4 style={{ color: themeColors.text }}>Introduce Topic</h4>
              <div className="form-row">
                <div className="form-group">
                  <label>Name *</label>
                  <input
                    type="text"
                    value={topicForm.name}
                    onChange={e => setTopicForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Topic name"
                  />
                </div>
                <div className="form-group">
                  <label>Relevance Score (0-1)</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={topicForm.relevance_score}
                    onChange={e => setTopicForm(f => ({ ...f, relevance_score: e.target.value }))}
                    placeholder="0.0 - 1.0"
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={topicForm.description}
                  onChange={e => setTopicForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Topic description"
                />
              </div>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary }}
                onClick={handleIntroduceTopic}
                disabled={!topicForm.name.trim()}
              >
                Introduce Topic
              </button>
            </div>
          )}

          {/* Session Summary */}
          {selectedStrategySession && sessionSummary && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Session Summary</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(sessionSummary, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DialogueManagerPanel;
