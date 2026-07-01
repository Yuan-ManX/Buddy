import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: indigo for cognitive horizon
const themeColors = {
  primary: '#4338ca',
  secondary: '#6366f1',
  bg: '#eef2ff',
  border: '#c7d2fe',
  accent: '#e0e7ff',
  text: '#312e81',
};

// Enum values must match backend KnowledgeDomain / CompetenceLevel / HorizonProximity / BoundaryResponse exactly (uppercase).
const KNOWLEDGE_DOMAINS = ['REASONING', 'PLANNING', 'MEMORY', 'LANGUAGE', 'PERCEPTION', 'TOOL_USE', 'COLLABORATION', 'CREATIVITY', 'ANALYTICS', 'CODING'];
const COMPETENCE_LEVELS = ['NOVICE', 'ADVANCED_BEGINNER', 'COMPETENT', 'PROFICIENT', 'EXPERT', 'MASTER'];
const HORIZON_PROXIMITIES = ['INTERIOR', 'NEAR', 'AT', 'BEYOND', 'UNCHARTED'];
const BOUNDARY_RESPONSES = ['PROCEED', 'PROCEED_WITH_CAUTION', 'LEARN', 'DEFER', 'REFER', 'ABSTAIN', 'ESCALATE'];

// Map a horizon proximity value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  INTERIOR: '#16a34a',
  NEAR: '#0ea5e9',
  AT: '#f59e0b',
  BEYOND: '#f97316',
  UNCHARTED: '#dc2626',
};

export const CognitiveHorizonPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'competence' | 'boundary'>('overview');

  // Competences / probes / events
  const [competences, setCompetences] = useState<any[]>([]);
  const [probes, setProbes] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [recommendResult, setRecommendResult] = useState<any>(null);
  const [learningResult, setLearningResult] = useState<any>(null);
  const [deferResult, setDeferResult] = useState<any>(null);

  // Register competence form
  const [competenceForm, setCompetenceForm] = useState({
    agent_id: '',
    domain: 'REASONING',
    level: 'NOVICE',
    confidence: '',
    success_rate: '',
    samples_seen: '',
  });

  // Probe form
  const [probeForm, setProbeForm] = useState({
    agent_id: '',
    domain: 'REASONING',
    probe_query: '',
  });

  // Record event form
  const [eventForm, setEventForm] = useState({
    agent_id: '',
    domain: 'REASONING',
    proximity: 'INTERIOR',
    response: 'PROCEED',
    trigger: '',
  });

  // Request learning form
  const [learningForm, setLearningForm] = useState({
    agent_id: '',
    domain: 'REASONING',
    trigger_probe_id: '',
    target_concept: '',
    urgency: '',
    estimated_effort: '',
  });

  // Defer decision form
  const [deferForm, setDeferForm] = useState({
    agent_id: '',
    domain: 'REASONING',
    deferred_to: '',
    reason: '',
    original_confidence: '',
    confidence_threshold: '',
  });

  // Recommend response form
  const [recommendForm, setRecommendForm] = useState({
    agent_id: '',
    domain: 'REASONING',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveHorizon.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive horizon stats');
    } finally {
      setLoading(false);
    }
  };

  const loadCompetences = async () => {
    try {
      const result = await api.cognitiveHorizon.listCompetences();
      const list = Array.isArray(result) ? result : (result?.competences ?? []);
      setCompetences(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load competences');
    }
  };

  const loadProbes = async () => {
    try {
      const result = await api.cognitiveHorizon.listProbes();
      const list = Array.isArray(result) ? result : (result?.probes ?? []);
      setProbes(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load probes');
    }
  };

  const loadEvents = async () => {
    try {
      const result = await api.cognitiveHorizon.listEvents();
      const list = Array.isArray(result) ? result : (result?.events ?? []);
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadCompetences();
      loadProbes();
      loadEvents();
    }
  }, [activeSection]);

  const handleRegisterCompetence = async () => {
    if (!competenceForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: competenceForm.agent_id.trim(),
      domain: competenceForm.domain,
      level: competenceForm.level,
    };
    if (competenceForm.confidence.trim()) payload.confidence = Number(competenceForm.confidence);
    if (competenceForm.success_rate.trim()) payload.success_rate = Number(competenceForm.success_rate);
    if (competenceForm.samples_seen.trim()) payload.samples_seen = Number(competenceForm.samples_seen);
    try {
      await api.cognitiveHorizon.registerCompetence(payload);
      toast.success('Competence registered');
      setCompetenceForm({ agent_id: '', domain: 'REASONING', level: 'NOVICE', confidence: '', success_rate: '', samples_seen: '' });
      await loadCompetences();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleProbe = async () => {
    if (!probeForm.agent_id.trim() || !probeForm.probe_query.trim()) {
      toast.error('Agent ID and probe query are required');
      return;
    }
    const payload: any = {
      agent_id: probeForm.agent_id.trim(),
      domain: probeForm.domain,
      probe_query: probeForm.probe_query.trim(),
    };
    try {
      await api.cognitiveHorizon.probe(payload);
      toast.success('Probe recorded');
      setProbeForm({ agent_id: '', domain: 'REASONING', probe_query: '' });
      await loadProbes();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordEvent = async () => {
    if (!eventForm.agent_id.trim() || !eventForm.trigger.trim()) {
      toast.error('Agent ID and trigger are required');
      return;
    }
    const payload: any = {
      agent_id: eventForm.agent_id.trim(),
      domain: eventForm.domain,
      proximity: eventForm.proximity,
      response: eventForm.response,
      trigger: eventForm.trigger.trim(),
    };
    try {
      await api.cognitiveHorizon.recordEvent(payload);
      toast.success('Event recorded');
      setEventForm({ agent_id: '', domain: 'REASONING', proximity: 'INTERIOR', response: 'PROCEED', trigger: '' });
      await loadEvents();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRequestLearning = async () => {
    if (!learningForm.agent_id.trim() || !learningForm.trigger_probe_id.trim() || !learningForm.target_concept.trim()) {
      toast.error('Agent ID, trigger probe ID, and target concept are required');
      return;
    }
    const payload: any = {
      agent_id: learningForm.agent_id.trim(),
      domain: learningForm.domain,
      trigger_probe_id: learningForm.trigger_probe_id.trim(),
      target_concept: learningForm.target_concept.trim(),
    };
    if (learningForm.urgency.trim()) payload.urgency = Number(learningForm.urgency);
    if (learningForm.estimated_effort.trim()) payload.estimated_effort = Number(learningForm.estimated_effort);
    try {
      const result = await api.cognitiveHorizon.requestLearning(payload);
      setLearningResult(result);
      toast.success('Learning requested');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeferDecision = async () => {
    if (!deferForm.agent_id.trim() || !deferForm.deferred_to.trim() || !deferForm.reason.trim() || !deferForm.original_confidence.trim()) {
      toast.error('Agent ID, deferred to, reason, and original confidence are required');
      return;
    }
    const payload: any = {
      agent_id: deferForm.agent_id.trim(),
      domain: deferForm.domain,
      deferred_to: deferForm.deferred_to.trim(),
      reason: deferForm.reason.trim(),
      original_confidence: Number(deferForm.original_confidence),
    };
    if (deferForm.confidence_threshold.trim()) payload.confidence_threshold = Number(deferForm.confidence_threshold);
    try {
      const result = await api.cognitiveHorizon.deferDecision(payload);
      setDeferResult(result);
      toast.success('Decision deferred');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecommendResponse = async () => {
    if (!recommendForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      const result = await api.cognitiveHorizon.recommendResponse(recommendForm.agent_id.trim(), recommendForm.domain);
      setRecommendResult(result);
      toast.success('Recommendation computed');
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
          <h2>🧭 Cognitive Horizon</h2>
          <p className="panel-subtitle">Register competence, probe boundaries, and learn at the frontier</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive horizon...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧭 Cognitive Horizon</h2>
        <p className="panel-subtitle">Register competence, probe boundaries, and learn at the frontier</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_competences ?? '-'}</span><span className="stat-label">Competences</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_probes ?? '-'}</span><span className="stat-label">Probes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_learning_requests ?? '-'}</span><span className="stat-label">Learning</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_defers ?? '-'}</span><span className="stat-label">Defers</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'competence', 'boundary'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Horizon Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Competences</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_competences ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Probes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_probes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_events ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Learning Requests</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_learning_requests ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Defers</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_defers ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Competences</h3>
            <button onClick={() => loadCompetences()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {competences.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No competences registered. Register one in the Competence section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {competences.slice(0, 10).map((c: any, i: number) => {
                  const id = c.competence_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>competence {id} · confidence: {c.confidence ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.domain && renderBadge(c.domain, themeColors.secondary)}
                          {c.level && renderBadge(c.level, themeColors.primary)}
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

      {/* Competence Section */}
      {activeSection === 'competence' && (
        <div className="dashboard-section">
          {/* Register Competence */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Competence</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={competenceForm.agent_id} onChange={e => setCompetenceForm({ ...competenceForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Domain</label>
                <select value={competenceForm.domain} onChange={e => setCompetenceForm({ ...competenceForm, domain: e.target.value })}>
                  {KNOWLEDGE_DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Level</label>
                <select value={competenceForm.level} onChange={e => setCompetenceForm({ ...competenceForm, level: e.target.value })}>
                  {COMPETENCE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Confidence</label>
                <input value={competenceForm.confidence} onChange={e => setCompetenceForm({ ...competenceForm, confidence: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group">
                <label>Success Rate</label>
                <input value={competenceForm.success_rate} onChange={e => setCompetenceForm({ ...competenceForm, success_rate: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.85" />
              </div>
              <div className="form-group">
                <label>Samples Seen</label>
                <input value={competenceForm.samples_seen} onChange={e => setCompetenceForm({ ...competenceForm, samples_seen: e.target.value })} type="number" min="0" placeholder="e.g. 120" />
              </div>
            </div>
            <button onClick={handleRegisterCompetence} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Competence</button>
          </div>

          {/* Probe */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Probe</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={probeForm.agent_id} onChange={e => setProbeForm({ ...probeForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Domain</label>
                <select value={probeForm.domain} onChange={e => setProbeForm({ ...probeForm, domain: e.target.value })}>
                  {KNOWLEDGE_DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Probe Query *</label>
                <input value={probeForm.probe_query} onChange={e => setProbeForm({ ...probeForm, probe_query: e.target.value })} placeholder="e.g. solve quantum entanglement paradox" />
              </div>
            </div>
            <button onClick={handleProbe} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Probe</button>
          </div>

          {/* Competences List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Competences ({competences.length})</h3>
            <button onClick={() => loadCompetences()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {competences.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No competences registered. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {competences.slice(0, 30).map((c: any, i: number) => {
                  const id = c.competence_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>competence {id} · success: {c.success_rate ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.domain && renderBadge(c.domain, themeColors.secondary)}
                          {c.level && renderBadge(c.level, themeColors.primary)}
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

      {/* Boundary Section */}
      {activeSection === 'boundary' && (
        <div className="dashboard-section">
          {/* Record Event */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Event</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={eventForm.agent_id} onChange={e => setEventForm({ ...eventForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Domain</label>
                <select value={eventForm.domain} onChange={e => setEventForm({ ...eventForm, domain: e.target.value })}>
                  {KNOWLEDGE_DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Proximity</label>
                <select value={eventForm.proximity} onChange={e => setEventForm({ ...eventForm, proximity: e.target.value })}>
                  {HORIZON_PROXIMITIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Response</label>
                <select value={eventForm.response} onChange={e => setEventForm({ ...eventForm, response: e.target.value })}>
                  {BOUNDARY_RESPONSES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Trigger *</label>
                <input value={eventForm.trigger} onChange={e => setEventForm({ ...eventForm, trigger: e.target.value })} placeholder="trigger description" />
              </div>
            </div>
            <button onClick={handleRecordEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Event</button>
          </div>

          {/* Request Learning */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Request Learning</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={learningForm.agent_id} onChange={e => setLearningForm({ ...learningForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Domain</label>
                <select value={learningForm.domain} onChange={e => setLearningForm({ ...learningForm, domain: e.target.value })}>
                  {KNOWLEDGE_DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Trigger Probe ID *</label>
                <input value={learningForm.trigger_probe_id} onChange={e => setLearningForm({ ...learningForm, trigger_probe_id: e.target.value })} placeholder="probe id" />
              </div>
              <div className="form-group">
                <label>Target Concept *</label>
                <input value={learningForm.target_concept} onChange={e => setLearningForm({ ...learningForm, target_concept: e.target.value })} placeholder="e.g. tensor_calculus" />
              </div>
              <div className="form-group">
                <label>Urgency</label>
                <input value={learningForm.urgency} onChange={e => setLearningForm({ ...learningForm, urgency: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Estimated Effort</label>
                <input value={learningForm.estimated_effort} onChange={e => setLearningForm({ ...learningForm, estimated_effort: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 12.5" />
              </div>
            </div>
            <button onClick={handleRequestLearning} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Request Learning</button>
            {learningResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(learningResult, null, 2)}</pre>
            )}
          </div>

          {/* Defer Decision */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Defer Decision</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={deferForm.agent_id} onChange={e => setDeferForm({ ...deferForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Domain</label>
                <select value={deferForm.domain} onChange={e => setDeferForm({ ...deferForm, domain: e.target.value })}>
                  {KNOWLEDGE_DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Deferred To *</label>
                <input value={deferForm.deferred_to} onChange={e => setDeferForm({ ...deferForm, deferred_to: e.target.value })} placeholder="e.g. expert_agent_7" />
              </div>
              <div className="form-group">
                <label>Original Confidence *</label>
                <input value={deferForm.original_confidence} onChange={e => setDeferForm({ ...deferForm, original_confidence: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.3" />
              </div>
              <div className="form-group">
                <label>Confidence Threshold</label>
                <input value={deferForm.confidence_threshold} onChange={e => setDeferForm({ ...deferForm, confidence_threshold: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Reason *</label>
                <input value={deferForm.reason} onChange={e => setDeferForm({ ...deferForm, reason: e.target.value })} placeholder="defer rationale" />
              </div>
            </div>
            <button onClick={handleDeferDecision} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Defer Decision</button>
            {deferResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(deferResult, null, 2)}</pre>
            )}
          </div>

          {/* Recommend Response */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recommend Response</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={recommendForm.agent_id} onChange={e => setRecommendForm({ ...recommendForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Domain</label>
                <select value={recommendForm.domain} onChange={e => setRecommendForm({ ...recommendForm, domain: e.target.value })}>
                  {KNOWLEDGE_DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRecommendResponse} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Recommend</button>
            {recommendResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(recommendResult, null, 2)}</pre>
            )}
          </div>

          {/* Events List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Events ({events.length})</h3>
            <button onClick={() => loadEvents()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {events.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No events recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {events.slice(0, 30).map((e: any, i: number) => {
                  const id = e.event_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>event {id}{e.trigger ? ` · ${e.trigger}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.domain && renderBadge(e.domain, themeColors.secondary)}
                          {e.proximity && renderBadge(e.proximity, statusColor(e.proximity))}
                          {e.response && renderBadge(e.response, themeColors.primary)}
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

export default CognitiveHorizonPanel;
