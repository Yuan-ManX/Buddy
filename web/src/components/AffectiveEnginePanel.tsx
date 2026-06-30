import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: rose for affective engine
const themeColors = {
  primary: '#e11d48',
  secondary: '#f43f5e',
  bg: '#fff1f2',
  border: '#fecdd3',
  accent: '#ffe4e6',
  text: '#881337',
};

// Enum values must match backend EmotionType / RegulationStrategy / AppraisalDimension / AffectiveMode / TriggerType exactly (uppercase).
const EMOTION_TYPES = ['JOY', 'FRUSTRATION', 'CURIOSITY', 'ANXIETY', 'SATISFACTION', 'CONFUSION', 'ENTHUSIASM', 'CALM', 'SADNESS', 'SURPRISE'];
const REGULATION_STRATEGIES = ['REAPPRAISAL', 'SUPPRESSION', 'REDIRECTION', 'ACCEPTANCE', 'AMPLIFICATION'];
const APPRAISAL_DIMENSIONS = ['NOVELTY', 'VALENCE', 'GOAL_CONGRUENCE', 'AGENCY', 'CERTAINTY'];
const AFFECTIVE_MODES = ['NEUTRAL', 'ENGAGED', 'STRESSED', 'EXPLORATORY', 'REFLECTIVE'];
const TRIGGER_TYPES = ['EVENT', 'GOAL_PROGRESS', 'SOCIAL', 'INTERNAL', 'ENVIRONMENT'];

// Map a mode value to a badge color for at-a-glance scanning.
const MODE_COLORS: Record<string, string> = {
  NEUTRAL: '#9ca3af',
  ENGAGED: '#0d9488',
  STRESSED: '#dc2626',
  EXPLORATORY: '#d97706',
  REFLECTIVE: '#6366f1',
};

export const AffectiveEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'profile' | 'emotion'>('overview');

  // Profiles / states / selected agent / results
  const [profiles, setProfiles] = useState<any[]>([]);
  const [states, setStates] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [appraiseResult, setAppraiseResult] = useState<any>(null);
  const [generateResult, setGenerateResult] = useState<any>(null);
  const [regulateResult, setRegulateResult] = useState<any>(null);
  const [mirrorResult, setMirrorResult] = useState<any>(null);

  // Profile form
  const [profileForm, setProfileForm] = useState({
    agent_id: '',
    name: '',
  });

  // Appraise event form
  const [appraiseForm, setAppraiseForm] = useState({
    agent_id: '',
    trigger_type: 'EVENT',
    event_description: '',
    appraisal_scores: '',
  });

  // Generate emotion form
  const [generateForm, setGenerateForm] = useState({
    agent_id: '',
    appraisal_id: '',
  });

  // Regulate form
  const [regulateForm, setRegulateForm] = useState({
    agent_id: '',
    strategy: 'REAPPRAISAL',
    target_emotion: 'FRUSTRATION',
  });

  // Set mode form
  const [modeForm, setModeForm] = useState({
    agent_id: '',
    mode: 'ENGAGED',
  });

  // Mirror emotion form
  const [mirrorForm, setMirrorForm] = useState({
    agent_id: '',
    user_emotion: 'JOY',
    intensity: '0.5',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.affectiveEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load affective engine stats');
    } finally {
      setLoading(false);
    }
  };

  const loadProfiles = async () => {
    try {
      const result = await api.affectiveEngine.listProfiles();
      const list = Array.isArray(result) ? result : (result?.profiles ?? []);
      setProfiles(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load profiles');
    }
  };

  const loadStates = async () => {
    if (!selectedAgent) { setStates([]); return; }
    try {
      const result = await api.affectiveEngine.getCurrentState(selectedAgent);
      // Current state is a single object; wrap into a list for uniform rendering.
      setStates(result ? [result] : []);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load current state');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadProfiles();
    }
  }, [activeSection]);

  // Reload current state when selected agent changes
  useEffect(() => { loadStates(); }, [selectedAgent]);

  const handleRegisterAgent = async () => {
    if (!profileForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = { agent_id: profileForm.agent_id.trim() };
    if (profileForm.name.trim()) payload.name = profileForm.name.trim();
    try {
      await api.affectiveEngine.registerAgent(payload);
      toast.success('Agent profile registered');
      setProfileForm({ agent_id: '', name: '' });
      await loadProfiles();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAppraiseEvent = async () => {
    if (!appraiseForm.agent_id.trim() || !appraiseForm.event_description.trim()) {
      toast.error('Agent ID and event description are required');
      return;
    }
    const payload: any = {
      agent_id: appraiseForm.agent_id.trim(),
      trigger_type: appraiseForm.trigger_type,
      event_description: appraiseForm.event_description.trim(),
    };
    if (appraiseForm.appraisal_scores.trim()) {
      try { payload.appraisal_scores = JSON.parse(appraiseForm.appraisal_scores); }
      catch { toast.error('Appraisal scores must be valid JSON'); return; }
    }
    try {
      const result = await api.affectiveEngine.appraiseEvent(payload);
      setAppraiseResult(result);
      toast.success('Event appraised');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGenerateEmotion = async () => {
    if (!generateForm.agent_id.trim() || !generateForm.appraisal_id.trim()) {
      toast.error('Agent ID and appraisal ID are required');
      return;
    }
    try {
      const result = await api.affectiveEngine.generateEmotion({
        agent_id: generateForm.agent_id.trim(),
        appraisal_id: generateForm.appraisal_id.trim(),
      });
      setGenerateResult(result);
      toast.success('Emotion generated');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRegulate = async () => {
    if (!regulateForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: regulateForm.agent_id.trim(),
      strategy: regulateForm.strategy,
    };
    if (regulateForm.target_emotion.trim()) payload.target_emotion = regulateForm.target_emotion;
    try {
      const result = await api.affectiveEngine.regulateEmotion(payload);
      setRegulateResult(result);
      toast.success('Regulation applied');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSetMode = async () => {
    if (!modeForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      await api.affectiveEngine.setMode(modeForm.agent_id.trim(), modeForm.mode);
      toast.success('Mode set');
      if (selectedAgent === modeForm.agent_id.trim()) await loadStates();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMirrorEmotion = async () => {
    if (!mirrorForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: mirrorForm.agent_id.trim(),
      user_emotion: mirrorForm.user_emotion,
    };
    if (mirrorForm.intensity.trim() !== '') payload.intensity = Number(mirrorForm.intensity);
    try {
      const result = await api.affectiveEngine.mirrorEmotion(payload);
      setMirrorResult(result);
      toast.success('Emotion mirrored');
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

  const modeColor = (m: string) => MODE_COLORS[m] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>💗 Affective Engine</h2>
          <p className="panel-subtitle">Register affective profiles, appraise events, and regulate agent emotions</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading affective engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💗 Affective Engine</h2>
        <p className="panel-subtitle">Register affective profiles, appraise events, and regulate agent emotions</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_profiles ?? '-'}</span><span className="stat-label">Profiles</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_appraisals ?? '-'}</span><span className="stat-label">Appraisals</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_emotions ?? '-'}</span><span className="stat-label">Emotions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_regulations ?? '-'}</span><span className="stat-label">Regulations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_modes ?? '-'}</span><span className="stat-label">Active Modes</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'profile', 'emotion'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Affective Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Profiles</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_profiles ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Appraisals</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_appraisals ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Emotions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_emotions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Regulations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_regulations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Modes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_modes ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Profiles</h3>
            <button onClick={() => loadProfiles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {profiles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No profiles recorded. Register one in the Profile section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {profiles.slice(0, 10).map((p: any, i: number) => {
                  const id = p.agent_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{p.name ?? 'unnamed'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Profile Section */}
      {activeSection === 'profile' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Agent</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={profileForm.agent_id} onChange={e => setProfileForm({ ...profileForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Name</label>
                <input value={profileForm.name} onChange={e => setProfileForm({ ...profileForm, name: e.target.value })} placeholder="Optional display name" />
              </div>
            </div>
            <button onClick={handleRegisterAgent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Agent</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Profiles ({profiles.length})</h3>
            <button onClick={() => loadProfiles()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {profiles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No profiles recorded. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {profiles.slice(0, 30).map((p: any, i: number) => {
                  const id = p.agent_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{p.name ?? 'unnamed'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div>
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => setSelectedAgent(id)}>View State</button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {selectedAgent && (
              <div style={{ marginTop: 12, padding: 8, background: themeColors.accent, borderRadius: 6, color: themeColors.text, fontSize: 13 }}>
                Current state for: <strong>{selectedAgent}</strong>
                {states.length === 0 ? (
                  <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>No current state available.</div>
                ) : (
                  <pre style={{ background: '#fff', padding: 8, borderRadius: 4, marginTop: 6, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(states[0], null, 2)}</pre>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Emotion Section */}
      {activeSection === 'emotion' && (
        <div className="dashboard-section">
          {/* Appraise Event */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Appraise Event</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={appraiseForm.agent_id} onChange={e => setAppraiseForm({ ...appraiseForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Trigger Type</label>
                <select value={appraiseForm.trigger_type} onChange={e => setAppraiseForm({ ...appraiseForm, trigger_type: e.target.value })}>
                  {TRIGGER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Event Description *</label>
                <input value={appraiseForm.event_description} onChange={e => setAppraiseForm({ ...appraiseForm, event_description: e.target.value })} placeholder="What happened?" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Appraisal Scores (JSON)</label>
                <input value={appraiseForm.appraisal_scores} onChange={e => setAppraiseForm({ ...appraiseForm, appraisal_scores: e.target.value })} placeholder='{"NOVELTY": 0.8, "VALENCE": -0.3}' />
              </div>
            </div>
            <button onClick={handleAppraiseEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Appraise</button>
            {appraiseResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(appraiseResult, null, 2)}</pre>
            )}
          </div>

          {/* Generate Emotion */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Generate Emotion</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={generateForm.agent_id} onChange={e => setGenerateForm({ ...generateForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Appraisal ID *</label>
                <input value={generateForm.appraisal_id} onChange={e => setGenerateForm({ ...generateForm, appraisal_id: e.target.value })} placeholder="appraisal id" />
              </div>
            </div>
            <button onClick={handleGenerateEmotion} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Generate</button>
            {generateResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(generateResult, null, 2)}</pre>
            )}
          </div>

          {/* Regulate */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Regulate Emotion</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={regulateForm.agent_id} onChange={e => setRegulateForm({ ...regulateForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={regulateForm.strategy} onChange={e => setRegulateForm({ ...regulateForm, strategy: e.target.value })}>
                  {REGULATION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Emotion</label>
                <select value={regulateForm.target_emotion} onChange={e => setRegulateForm({ ...regulateForm, target_emotion: e.target.value })}>
                  {EMOTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRegulate} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Regulate</button>
            {regulateResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(regulateResult, null, 2)}</pre>
            )}
          </div>

          {/* Set Mode */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Set Affective Mode</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={modeForm.agent_id} onChange={e => setModeForm({ ...modeForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Mode</label>
                <select value={modeForm.mode} onChange={e => setModeForm({ ...modeForm, mode: e.target.value })}>
                  {AFFECTIVE_MODES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleSetMode} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Set Mode</button>
            <div style={{ marginTop: 8, fontSize: 12, color: themeColors.text, opacity: 0.7 }}>
              Modes: {AFFECTIVE_MODES.map(m => renderBadge(m, modeColor(m)))}
            </div>
          </div>

          {/* Mirror Emotion */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Mirror Emotion</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={mirrorForm.agent_id} onChange={e => setMirrorForm({ ...mirrorForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>User Emotion</label>
                <select value={mirrorForm.user_emotion} onChange={e => setMirrorForm({ ...mirrorForm, user_emotion: e.target.value })}>
                  {EMOTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Intensity</label>
                <input value={mirrorForm.intensity} onChange={e => setMirrorForm({ ...mirrorForm, intensity: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
            </div>
            <button onClick={handleMirrorEmotion} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Mirror</button>
            {mirrorResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(mirrorResult, null, 2)}</pre>
            )}
          </div>

          {/* Current State */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Current State</h3>
            <div style={{ marginBottom: 12 }}>
              <input
                value={selectedAgent}
                onChange={e => setSelectedAgent(e.target.value)}
                placeholder="Enter agent ID to view current state"
                style={{ marginRight: 8, padding: '6px 8px' }}
              />
              <button onClick={() => loadStates()} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Refresh</button>
            </div>
            {states.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No current state. Enter an agent ID above.</div>
            ) : (
              states.map((st: any, i: number) => {
                const id = st.state_id ?? st.agent_id ?? i;
                return (
                  <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {st.agent_id ?? selectedAgent}</div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                      </div>
                      <div>
                        {st.mode && renderBadge(st.mode, modeColor(st.mode))}
                        {st.dominant_emotion && renderBadge(st.dominant_emotion, themeColors.secondary)}
                      </div>
                    </div>
                    {st.emotions && (
                      <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 6, overflow: 'auto', maxHeight: 100, fontSize: 11 }}>{JSON.stringify(st.emotions, null, 2)}</pre>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AffectiveEnginePanel;
