import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: rose for ethical deliberation
const themeColors = {
  primary: '#e11d48',
  secondary: '#f43f5e',
  bg: '#fff1f2',
  border: '#fecdd3',
  accent: '#ffe4e6',
  text: '#881337',
};

// Enum values must match backend EthicalFramework / PrincipleCategory / VerdictType / StakeholderImpact exactly (lowercase).
const ETHICAL_FRAMEWORKS = ['utilitarian', 'deontological', 'virtue_ethics', 'care_ethics', 'justice_based', 'pragmatic'];
const PRINCIPLE_CATEGORIES = ['beneficence', 'non_maleficence', 'autonomy', 'justice', 'fidelity', 'honesty', 'fairness'];
const VERDICT_TYPES = ['permitted', 'prohibited', 'permitted_with_conditions', 'requires_review', 'inconclusive'];
const STAKEHOLDER_IMPACTS = ['positive', 'negative', 'neutral', 'mixed'];

const VERDICT_COLORS: Record<string, string> = {
  permitted: '#10b981',
  prohibited: '#ef4444',
  permitted_with_conditions: '#f59e0b',
  requires_review: '#3b82f6',
  inconclusive: '#6b7280',
};

export const EthicalDeliberationPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'dilemma' | 'deliberate'>('overview');

  // Dilemmas / stakeholders / consequences / verdict
  const [dilemmas, setDilemmas] = useState<any[]>([]);
  const [principles, setPrinciples] = useState<any[]>([]);
  const [selectedDilemmaId, setSelectedDilemmaId] = useState<string>('');
  const [dilemmaDetail, setDilemmaDetail] = useState<any>(null);
  const [verdict, setVerdict] = useState<any>(null);
  const [lastAssessment, setLastAssessment] = useState<any>(null);

  // Dilemma form
  const [dilemmaForm, setDilemmaForm] = useState({
    title: '',
    description: '',
    proposed_action: '',
  });

  // Stakeholder form
  const [stakeholderForm, setStakeholderForm] = useState({
    name: '',
    role: '',
    interests: '',
    vulnerability: '0.5',
  });

  // Consequence form
  const [consequenceForm, setConsequenceForm] = useState({
    stakeholder_id: '',
    stakeholder_name: '',
    impact: 'neutral',
    magnitude: '0.5',
    probability: '1.0',
    description: '',
  });

  // Quick assess form
  const [assessForm, setAssessForm] = useState({
    action_description: '',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.ethicalDeliberator.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load ethical deliberator stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDilemmas = useCallback(async () => {
    try {
      const result = await api.ethicalDeliberator.listDilemmas();
      const list = Array.isArray(result) ? result : (result?.dilemmas ?? []);
      setDilemmas(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load dilemmas');
    }
  }, [toast]);

  const loadPrinciples = useCallback(async () => {
    try {
      const result = await api.ethicalDeliberator.listPrinciples();
      const list = Array.isArray(result) ? result : (result?.principles ?? []);
      setPrinciples(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load principles');
    }
  }, [toast]);

  const loadDilemmaDetail = useCallback(async (dilemmaId: string) => {
    if (!dilemmaId) return;
    try {
      const detail = await api.ethicalDeliberator.getDilemma(dilemmaId);
      setDilemmaDetail(detail);
    } catch (e: any) {
      setDilemmaDetail(null);
    }
  }, []);

  const loadVerdict = useCallback(async (dilemmaId: string) => {
    if (!dilemmaId) return;
    try {
      const v = await api.ethicalDeliberator.getVerdictForDilemma(dilemmaId);
      setVerdict(v);
    } catch (e: any) {
      // Verdict may not exist until deliberation has been run
      setVerdict(null);
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + dilemmas when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadDilemmas();
      loadPrinciples();
    }
  }, [activeSection, loadStats, loadDilemmas, loadPrinciples]);

  // When dilemma changes, refresh its detail + verdict
  useEffect(() => {
    if (selectedDilemmaId) {
      loadDilemmaDetail(selectedDilemmaId);
      loadVerdict(selectedDilemmaId);
    }
  }, [selectedDilemmaId, loadDilemmaDetail, loadVerdict]);

  // Auto-select first dilemma when entering non-overview sections
  useEffect(() => {
    if (activeSection !== 'overview' && !selectedDilemmaId && dilemmas.length > 0) {
      setSelectedDilemmaId(dilemmas[0].dilemma_id ?? dilemmas[0].id);
    }
  }, [activeSection, selectedDilemmaId, dilemmas]);

  const handleSubmitDilemma = async () => {
    if (!dilemmaForm.title.trim() || !dilemmaForm.description.trim() || !dilemmaForm.proposed_action.trim()) {
      toast.error('Title, description, and proposed action are required');
      return;
    }
    try {
      const result = await api.ethicalDeliberator.submitDilemma({
        title: dilemmaForm.title.trim(),
        description: dilemmaForm.description.trim(),
        proposed_action: dilemmaForm.proposed_action.trim(),
      });
      toast.success('Dilemma submitted');
      setDilemmaForm({ title: '', description: '', proposed_action: '' });
      await loadDilemmas();
      const newId = result?.dilemma_id ?? result?.id;
      if (newId) setSelectedDilemmaId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddStakeholder = async () => {
    if (!selectedDilemmaId || !stakeholderForm.name.trim()) {
      toast.error('Dilemma and stakeholder name are required');
      return;
    }
    try {
      const payload: any = {
        name: stakeholderForm.name.trim(),
        vulnerability: Number(stakeholderForm.vulnerability),
      };
      if (stakeholderForm.role.trim()) payload.role = stakeholderForm.role.trim();
      if (stakeholderForm.interests.trim()) payload.interests = stakeholderForm.interests.split(',').map(s => s.trim()).filter(Boolean);
      await api.ethicalDeliberator.addStakeholder(selectedDilemmaId, payload);
      toast.success('Stakeholder added');
      setStakeholderForm({ name: '', role: '', interests: '', vulnerability: '0.5' });
      loadDilemmaDetail(selectedDilemmaId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddConsequence = async () => {
    if (!selectedDilemmaId || !consequenceForm.stakeholder_id.trim()) {
      toast.error('Dilemma and stakeholder ID are required');
      return;
    }
    try {
      const payload: any = {
        stakeholder_id: consequenceForm.stakeholder_id.trim(),
        impact: consequenceForm.impact,
        magnitude: Number(consequenceForm.magnitude),
        probability: Number(consequenceForm.probability),
      };
      if (consequenceForm.stakeholder_name.trim()) payload.stakeholder_name = consequenceForm.stakeholder_name.trim();
      if (consequenceForm.description.trim()) payload.description = consequenceForm.description.trim();
      await api.ethicalDeliberator.addConsequence(selectedDilemmaId, payload);
      toast.success('Consequence added');
      setConsequenceForm({ stakeholder_id: '', stakeholder_name: '', impact: 'neutral', magnitude: '0.5', probability: '1.0', description: '' });
      loadDilemmaDetail(selectedDilemmaId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeliberate = async () => {
    if (!selectedDilemmaId) return;
    try {
      const result = await api.ethicalDeliberator.deliberate(selectedDilemmaId);
      setVerdict(result);
      toast.success('Deliberation complete');
      loadDilemmaDetail(selectedDilemmaId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAssessAction = async () => {
    if (!assessForm.action_description.trim()) {
      toast.error('Action description is required');
      return;
    }
    try {
      const result = await api.ethicalDeliberator.assessAction(assessForm.action_description.trim());
      setLastAssessment(result);
      toast.success('Action assessed');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>⚖️ Ethical Deliberation</h2>
          <p className="panel-subtitle">Submit dilemmas, deliberate across frameworks, and review verdicts</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading ethical deliberator...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚖️ Ethical Deliberation</h2>
        <p className="panel-subtitle">Submit dilemmas, deliberate across frameworks, and review verdicts</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_dilemmas ?? '-'}</span><span className="stat-label">Dilemmas</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_verdicts ?? '-'}</span><span className="stat-label">Verdicts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.pending_dilemmas ?? '-'}</span><span className="stat-label">Pending</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_stakeholders ?? '-'}</span><span className="stat-label">Stakeholders</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_principles ?? '-'}</span><span className="stat-label">Principles</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'dilemma', 'deliberate'] as const).map(s => (
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

      {/* Dilemma selector shared across non-overview sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Dilemma</label>
          <select
            value={selectedDilemmaId}
            onChange={e => { setSelectedDilemmaId(e.target.value); setVerdict(null); }}
          >
            <option value="">— Select a dilemma —</option>
            {dilemmas.map((d: any) => {
              const id = d.dilemma_id ?? d.id;
              return <option key={id} value={id}>{d.title ?? id}</option>;
            })}
          </select>
        </div>
      )}

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Ethical Deliberation Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Dilemmas</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_dilemmas ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Verdicts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_verdicts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Pending Dilemmas</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.pending_dilemmas ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Stakeholders</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_stakeholders ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Principles</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_principles ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Dilemmas</h3>
            <button onClick={() => loadDilemmas()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {dilemmas.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No dilemmas recorded. Submit one in the Dilemma section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {dilemmas.slice(0, 10).map((d: any) => {
                  const id = d.dilemma_id ?? d.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{d.title ?? 'untitled'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{d.status ?? 'unknown'}]</span></div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setActiveSection('dilemma'); setSelectedDilemmaId(id); }}>Open</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dilemma Section */}
      {activeSection === 'dilemma' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Submit Dilemma</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Title *</label>
                <input value={dilemmaForm.title} onChange={e => setDilemmaForm({ ...dilemmaForm, title: e.target.value })} placeholder="e.g. self_disclosure_of_limitations" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description *</label>
                <textarea rows={3} value={dilemmaForm.description} onChange={e => setDilemmaForm({ ...dilemmaForm, description: e.target.value })} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Proposed Action *</label>
                <textarea rows={2} value={dilemmaForm.proposed_action} onChange={e => setDilemmaForm({ ...dilemmaForm, proposed_action: e.target.value })} />
              </div>
            </div>
            <button onClick={handleSubmitDilemma} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Submit Dilemma</button>
          </div>

          {selectedDilemmaId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Stakeholder</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input value={stakeholderForm.name} onChange={e => setStakeholderForm({ ...stakeholderForm, name: e.target.value })} placeholder="e.g. end_user" />
                  </div>
                  <div className="form-group">
                    <label>Role</label>
                    <input value={stakeholderForm.role} onChange={e => setStakeholderForm({ ...stakeholderForm, role: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Vulnerability (0-1)</label>
                    <input value={stakeholderForm.vulnerability} onChange={e => setStakeholderForm({ ...stakeholderForm, vulnerability: e.target.value })} type="number" min="0" max="1" step="0.1" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Interests (comma-separated)</label>
                    <input value={stakeholderForm.interests} onChange={e => setStakeholderForm({ ...stakeholderForm, interests: e.target.value })} placeholder="privacy, accuracy, speed" />
                  </div>
                </div>
                <button onClick={handleAddStakeholder} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Stakeholder</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Consequence</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Stakeholder ID *</label>
                    <input value={consequenceForm.stakeholder_id} onChange={e => setConsequenceForm({ ...consequenceForm, stakeholder_id: e.target.value })} placeholder="e.g. stk_xxx" list="stakeholder-options" />
                    <datalist id="stakeholder-options">
                      {(dilemmaDetail?.stakeholders ?? []).map((s: any) => <option key={s.stakeholder_id ?? s.id} value={s.stakeholder_id ?? s.id} />)}
                    </datalist>
                  </div>
                  <div className="form-group">
                    <label>Stakeholder Name</label>
                    <input value={consequenceForm.stakeholder_name} onChange={e => setConsequenceForm({ ...consequenceForm, stakeholder_name: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Impact</label>
                    <select value={consequenceForm.impact} onChange={e => setConsequenceForm({ ...consequenceForm, impact: e.target.value })}>
                      {STAKEHOLDER_IMPACTS.map(i => <option key={i} value={i}>{i}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Magnitude (0-1)</label>
                    <input value={consequenceForm.magnitude} onChange={e => setConsequenceForm({ ...consequenceForm, magnitude: e.target.value })} type="number" min="0" max="1" step="0.1" />
                  </div>
                  <div className="form-group">
                    <label>Probability (0-1)</label>
                    <input value={consequenceForm.probability} onChange={e => setConsequenceForm({ ...consequenceForm, probability: e.target.value })} type="number" min="0" max="1" step="0.1" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={consequenceForm.description} onChange={e => setConsequenceForm({ ...consequenceForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleAddConsequence} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Consequence</button>
              </div>

              {dilemmaDetail && (
                <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                  <h3 style={{ color: themeColors.text }}>Dilemma: {selectedDilemmaId}</h3>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(dilemmaDetail, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Deliberate Section */}
      {activeSection === 'deliberate' && (
        <div className="dashboard-section">
          {selectedDilemmaId && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Run Deliberation</h3>
              <p style={{ color: themeColors.text, opacity: 0.8, marginTop: 4 }}>Deliberate the active dilemma across all configured frameworks.</p>
              <button onClick={handleDeliberate} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Deliberate</button>
            </div>
          )}

          {verdict && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Verdict</h3>
              <div style={{ marginTop: 8, padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${VERDICT_COLORS[verdict.verdict_type] ?? themeColors.primary}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, textTransform: 'capitalize' }}>
                  Verdict: <span style={{ color: VERDICT_COLORS[verdict.verdict_type] ?? themeColors.primary }}>{verdict.verdict_type ?? 'unknown'}</span>
                </div>
                {verdict.confidence !== undefined && (
                  <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>confidence: {verdict.confidence?.toFixed?.(2) ?? verdict.confidence}</div>
                )}
                {(verdict.verdict_id ?? verdict.id) && (
                  <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{verdict.verdict_id ?? verdict.id}</div>
                )}
              </div>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(verdict, null, 2)}</pre>
            </div>
          )}

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Quick Assess Action</h3>
            <p style={{ color: themeColors.text, opacity: 0.8, marginTop: 4 }}>Run a lightweight ethical assessment of a single action.</p>
            <div className="form-group" style={{ marginTop: 12 }}>
              <label>Action Description *</label>
              <textarea rows={3} value={assessForm.action_description} onChange={e => setAssessForm({ ...assessForm, action_description: e.target.value })} />
            </div>
            <button onClick={handleAssessAction} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Assess</button>
            {lastAssessment && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(lastAssessment, null, 2)}</pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Configured Principles ({principles.length})</h3>
            <button onClick={() => loadPrinciples()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {principles.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No principles registered.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {principles.slice(0, 20).map((p: any, i: number) => {
                  const id = p.principle_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{p.name ?? 'principle'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{p.category ?? 'unknown'} · {p.framework ?? 'unknown'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>weight {p.weight ?? '-'} · {id}</div>
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

export default EthicalDeliberationPanel;
