import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: indigo for cognitive scaffolding
const themeColors = {
  primary: '#4f46e5',
  secondary: '#6366f1',
  bg: '#eef2ff',
  border: '#c7d2fe',
  accent: '#e0e7ff',
  text: '#312e81',
};

// Enum values must match backend ScaffoldingLevel / ScaffoldingStrategy / CompetenceLevel / FadingTrigger / ScaffoldStatus exactly (uppercase).
const SCAFFOLDING_LEVELS = ['CONCEPTUAL', 'PROCEDURAL', 'STRATEGIC', 'METACOGNITIVE'];
const SCAFFOLDING_STRATEGIES = ['HINT', 'EXAMPLE', 'DECOMPOSE', 'MODEL', 'PROMPT', 'FEEDBACK', 'QUESTION'];
const COMPETENCE_LEVELS = ['NOVICE', 'BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT'];
const FADING_TRIGGERS = ['MASTERY', 'TIME', 'ERROR_RATE', 'CONFIDENCE', 'EXPLICIT'];
const SCAFFOLD_STATUS = ['PROPOSED', 'ACTIVE', 'FADING', 'WITHDRAWN', 'FAILED'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  PROPOSED: '#9ca3af',
  ACTIVE: '#4f46e5',
  FADING: '#d97706',
  WITHDRAWN: '#0d9488',
  FAILED: '#dc2626',
};

export const CognitiveScaffoldingPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'learner' | 'scaffold'>('overview');

  // Learners / sessions / scaffolds / selected learner / selected session
  const [learners, setLearners] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [scaffolds, setScaffolds] = useState<any[]>([]);
  const [selectedLearner, setSelectedLearner] = useState<string>('');
  const [selectedSession, setSelectedSession] = useState<string>('');

  // Learner form
  const [learnerForm, setLearnerForm] = useState({
    learner_id: '',
    name: '',
  });

  // Session form
  const [sessionForm, setSessionForm] = useState({
    learner_id: '',
    task_description: '',
    skill_domain: '',
    target_level: 'INTERMEDIATE',
  });

  // Propose scaffold form
  const [scaffoldForm, setScaffoldForm] = useState({
    level: 'CONCEPTUAL',
    strategy: 'HINT',
    content: '',
    fading_trigger: 'MASTERY',
  });

  // Scaffold lifecycle forms (operate by scaffold id)
  const [scaffoldIdForm, setScaffoldIdForm] = useState('');
  const [fadeReason, setFadeReason] = useState('');
  const [withdrawOutcome, setWithdrawOutcome] = useState('success');
  const [fadingPlanMilestones, setFadingPlanMilestones] = useState('');

  // Session outcome form
  const [outcomeForm, setOutcomeForm] = useState({
    session_id: '',
    success: 'true',
    feedback: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveScaffolding.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive scaffolding stats');
    } finally {
      setLoading(false);
    }
  };

  const loadLearners = async () => {
    try {
      const result = await api.cognitiveScaffolding.listLearners();
      const list = Array.isArray(result) ? result : (result?.learners ?? []);
      setLearners(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load learners');
    }
  };

  const loadSessions = async () => {
    if (!selectedLearner) { setSessions([]); return; }
    try {
      const result = await api.cognitiveScaffolding.listSessions(selectedLearner);
      const list = Array.isArray(result) ? result : (result?.sessions ?? []);
      setSessions(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load sessions');
    }
  };

  const loadScaffolds = async () => {
    if (!selectedSession) { setScaffolds([]); return; }
    try {
      const result = await api.cognitiveScaffolding.listScaffolds(selectedSession);
      const list = Array.isArray(result) ? result : (result?.scaffolds ?? []);
      setScaffolds(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load scaffolds');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadLearners();
    }
  }, [activeSection]);

  // Reload sessions when selected learner changes
  useEffect(() => { loadSessions(); }, [selectedLearner]);

  // Reload scaffolds when selected session changes
  useEffect(() => { loadScaffolds(); }, [selectedSession]);

  const handleRegisterLearner = async () => {
    if (!learnerForm.learner_id.trim()) {
      toast.error('Learner ID is required');
      return;
    }
    const payload: any = { learner_id: learnerForm.learner_id.trim() };
    if (learnerForm.name.trim()) payload.name = learnerForm.name.trim();
    try {
      await api.cognitiveScaffolding.registerLearner(payload);
      toast.success('Learner registered');
      setLearnerForm({ learner_id: '', name: '' });
      await loadLearners();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateSession = async () => {
    if (!sessionForm.learner_id.trim() || !sessionForm.task_description.trim() || !sessionForm.skill_domain.trim()) {
      toast.error('Learner ID, task description, and skill domain are required');
      return;
    }
    const payload: any = {
      learner_id: sessionForm.learner_id.trim(),
      task_description: sessionForm.task_description.trim(),
      skill_domain: sessionForm.skill_domain.trim(),
      target_level: sessionForm.target_level,
    };
    try {
      await api.cognitiveScaffolding.createSession(payload);
      toast.success('Session created');
      setSessionForm({ learner_id: '', task_description: '', skill_domain: '', target_level: 'INTERMEDIATE' });
      if (selectedLearner === payload.learner_id) await loadSessions();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleProposeScaffold = async () => {
    if (!selectedSession || !scaffoldForm.content.trim()) {
      toast.error('Select a session and provide scaffold content');
      return;
    }
    const payload: any = {
      level: scaffoldForm.level,
      strategy: scaffoldForm.strategy,
      content: scaffoldForm.content.trim(),
      fading_trigger: scaffoldForm.fading_trigger,
    };
    try {
      await api.cognitiveScaffolding.proposeScaffold(selectedSession, payload);
      toast.success('Scaffold proposed');
      setScaffoldForm({ level: 'CONCEPTUAL', strategy: 'HINT', content: '', fading_trigger: 'MASTERY' });
      await loadScaffolds();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleActivateScaffold = async () => {
    if (!scaffoldIdForm.trim()) { toast.error('Scaffold ID is required'); return; }
    try {
      await api.cognitiveScaffolding.activateScaffold(scaffoldIdForm.trim());
      toast.success('Scaffold activated');
      await loadScaffolds();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFadeScaffold = async () => {
    if (!scaffoldIdForm.trim()) { toast.error('Scaffold ID is required'); return; }
    try {
      await api.cognitiveScaffolding.fadeScaffold(scaffoldIdForm.trim(), fadeReason.trim() || undefined);
      toast.success('Scaffold faded');
      await loadScaffolds();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleWithdrawScaffold = async () => {
    if (!scaffoldIdForm.trim()) { toast.error('Scaffold ID is required'); return; }
    try {
      await api.cognitiveScaffolding.withdrawScaffold(scaffoldIdForm.trim(), withdrawOutcome);
      toast.success('Scaffold withdrawn');
      await loadScaffolds();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateFadingPlan = async () => {
    if (!scaffoldIdForm.trim()) { toast.error('Scaffold ID is required'); return; }
    let milestones: any[] = [];
    if (fadingPlanMilestones.trim()) {
      try { milestones = JSON.parse(fadingPlanMilestones); }
      catch { toast.error('Milestones must be a valid JSON array'); return; }
    }
    try {
      await api.cognitiveScaffolding.createFadingPlan(scaffoldIdForm.trim(), milestones);
      toast.success('Fading plan created');
      setFadingPlanMilestones('');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordOutcome = async () => {
    if (!outcomeForm.session_id.trim()) { toast.error('Session ID is required'); return; }
    const payload: any = { success: outcomeForm.success === 'true' };
    if (outcomeForm.feedback.trim()) payload.feedback = outcomeForm.feedback.trim();
    try {
      await api.cognitiveScaffolding.recordOutcome(outcomeForm.session_id.trim(), payload);
      toast.success('Outcome recorded');
      setOutcomeForm({ session_id: '', success: 'true', feedback: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const renderBadge = (value: string, color: string) => (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 10,
      fontSize: 11,
      fontWeight: 600,
      color: '#fff',
      background: color,
      marginRight: 4,
    }}>{value}</span>
  );

  const statusColor = (s: string) => STATUS_COLORS[s] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🪜 Cognitive Scaffolding</h2>
          <p className="panel-subtitle">Register learners, propose scaffolds, and orchestrate fading plans</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive scaffolding...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🪜 Cognitive Scaffolding</h2>
        <p className="panel-subtitle">Register learners, propose scaffolds, and orchestrate fading plans</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_learners ?? '-'}</span><span className="stat-label">Learners</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_sessions ?? '-'}</span><span className="stat-label">Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_scaffolds ?? '-'}</span><span className="stat-label">Scaffolds</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_count ?? '-'}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.withdrawn_count ?? '-'}</span><span className="stat-label">Withdrawn</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'learner', 'scaffold'] as const).map(s => (
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

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Cognitive Scaffolding Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Learners</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_learners ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Sessions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_sessions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Scaffolds</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_scaffolds ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_count ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Withdrawn</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.withdrawn_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Learners</h3>
            <button onClick={() => loadLearners()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {learners.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No learners recorded. Register one in the Learner section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {learners.slice(0, 10).map((l: any, i: number) => {
                  const id = l.learner_id ?? l.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{l.name ?? 'unnamed'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Learner Section */}
      {activeSection === 'learner' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Learner</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Learner ID *</label>
                <input value={learnerForm.learner_id} onChange={e => setLearnerForm({ ...learnerForm, learner_id: e.target.value })} placeholder="e.g. learner_1" />
              </div>
              <div className="form-group">
                <label>Name</label>
                <input value={learnerForm.name} onChange={e => setLearnerForm({ ...learnerForm, name: e.target.value })} placeholder="Optional display name" />
              </div>
            </div>
            <button onClick={handleRegisterLearner} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Learner</button>
          </div>

          {/* Create Session */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Session</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Learner ID *</label>
                <input value={sessionForm.learner_id} onChange={e => setSessionForm({ ...sessionForm, learner_id: e.target.value })} placeholder="learner id" />
              </div>
              <div className="form-group">
                <label>Skill Domain *</label>
                <input value={sessionForm.skill_domain} onChange={e => setSessionForm({ ...sessionForm, skill_domain: e.target.value })} placeholder="e.g. debugging" />
              </div>
              <div className="form-group">
                <label>Target Level</label>
                <select value={sessionForm.target_level} onChange={e => setSessionForm({ ...sessionForm, target_level: e.target.value })}>
                  {COMPETENCE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Task Description *</label>
                <input value={sessionForm.task_description} onChange={e => setSessionForm({ ...sessionForm, task_description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreateSession} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Session</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Learners ({learners.length})</h3>
            <button onClick={() => loadLearners()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {learners.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No learners recorded. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {learners.slice(0, 30).map((l: any, i: number) => {
                  const id = l.learner_id ?? l.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{l.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div>
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => { setSelectedLearner(id); setSelectedSession(''); }}>View Sessions</button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {selectedLearner && (
              <div style={{ marginTop: 12, padding: 8, background: themeColors.accent, borderRadius: 6, color: themeColors.text, fontSize: 13 }}>
                Selected learner: <strong>{selectedLearner}</strong>
                <div style={{ marginTop: 8 }}>Sessions:</div>
                {sessions.length === 0 ? (
                  <div style={{ fontSize: 12, opacity: 0.7 }}>No sessions for this learner.</div>
                ) : (
                  <div style={{ display: 'grid', gap: 6, marginTop: 6 }}>
                    {sessions.slice(0, 10).map((s: any, i: number) => {
                      const id = s.session_id ?? s.id ?? i;
                      return (
                        <div key={id} style={{ padding: 8, background: '#fff', borderRadius: 4, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                          <div>
                            <div style={{ fontWeight: 600, color: themeColors.text, fontSize: 13 }}>{s.task_description ?? 'no task'}</div>
                            <div style={{ fontSize: 11, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                          </div>
                          <button className="btn-sm" style={{ background: themeColors.secondary, color: '#fff' }} onClick={() => setSelectedSession(id)}>View Scaffolds</button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Scaffold Section */}
      {activeSection === 'scaffold' && (
        <div className="dashboard-section">
          <div style={{ padding: 12, background: themeColors.accent, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16, color: themeColors.text }}>
            Working on session: <strong>{selectedSession || 'none selected'}</strong> — pick a learner and a session in the Learner section first.
          </div>

          {/* Propose Scaffold */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Propose Scaffold</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Level</label>
                <select value={scaffoldForm.level} onChange={e => setScaffoldForm({ ...scaffoldForm, level: e.target.value })}>
                  {SCAFFOLDING_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={scaffoldForm.strategy} onChange={e => setScaffoldForm({ ...scaffoldForm, strategy: e.target.value })}>
                  {SCAFFOLDING_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Fading Trigger</label>
                <select value={scaffoldForm.fading_trigger} onChange={e => setScaffoldForm({ ...scaffoldForm, fading_trigger: e.target.value })}>
                  {FADING_TRIGGERS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Content *</label>
                <input value={scaffoldForm.content} onChange={e => setScaffoldForm({ ...scaffoldForm, content: e.target.value })} placeholder="Scaffold content" />
              </div>
            </div>
            <button onClick={handleProposeScaffold} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Propose Scaffold</button>
          </div>

          {/* Scaffold Lifecycle */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Scaffold Lifecycle</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Scaffold ID *</label>
                <input value={scaffoldIdForm} onChange={e => setScaffoldIdForm(e.target.value)} placeholder="scaffold id" />
              </div>
              <div className="form-group">
                <label>Fade Reason</label>
                <input value={fadeReason} onChange={e => setFadeReason(e.target.value)} placeholder="optional reason" />
              </div>
              <div className="form-group">
                <label>Withdraw Outcome</label>
                <select value={withdrawOutcome} onChange={e => setWithdrawOutcome(e.target.value)}>
                  <option value="success">success</option>
                  <option value="failure">failure</option>
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Fading Plan Milestones (JSON array)</label>
                <input value={fadingPlanMilestones} onChange={e => setFadingPlanMilestones(e.target.value)} placeholder='[{"trigger":"MASTERY","threshold":0.9}]' />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              <button onClick={handleActivateScaffold} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Activate</button>
              <button onClick={handleFadeScaffold} className="btn-sm" style={{ background: themeColors.secondary, color: '#fff' }}>Fade</button>
              <button onClick={handleWithdrawScaffold} className="btn-sm" style={{ background: '#0d9488', color: '#fff' }}>Withdraw</button>
              <button onClick={handleCreateFadingPlan} className="btn-sm" style={{ background: '#6366f1', color: '#fff' }}>Create Fading Plan</button>
            </div>
          </div>

          {/* Record Outcome */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Session Outcome</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Session ID *</label>
                <input value={outcomeForm.session_id} onChange={e => setOutcomeForm({ ...outcomeForm, session_id: e.target.value })} placeholder="session id" />
              </div>
              <div className="form-group">
                <label>Success</label>
                <select value={outcomeForm.success} onChange={e => setOutcomeForm({ ...outcomeForm, success: e.target.value })}>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Feedback</label>
                <input value={outcomeForm.feedback} onChange={e => setOutcomeForm({ ...outcomeForm, feedback: e.target.value })} />
              </div>
            </div>
            <button onClick={handleRecordOutcome} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Outcome</button>
          </div>

          {/* Scaffolds List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Scaffolds ({scaffolds.length})</h3>
            <button onClick={() => loadScaffolds()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {scaffolds.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No scaffolds recorded for the selected session.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {scaffolds.slice(0, 30).map((sc: any, i: number) => {
                  const id = sc.scaffold_id ?? sc.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{sc.content ?? 'no content'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {sc.level && renderBadge(sc.level, themeColors.secondary)}
                          {sc.strategy && renderBadge(sc.strategy, '#6366f1')}
                          {sc.status && renderBadge(sc.status, statusColor(sc.status))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CognitiveScaffoldingPanel;
