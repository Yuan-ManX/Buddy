import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: indigo for explanation synthesis
const themeColors = {
  primary: '#4f46e5',
  secondary: '#6366f1',
  bg: '#eef2ff',
  border: '#c7d2fe',
  accent: '#e0e7ff',
  text: '#312e81',
};

// Enum values must match backend ExplanationType / AudienceLevel / EvidenceType exactly (lowercase).
const EXPLANATION_TYPES = ['decision', 'reasoning', 'causal', 'contrastive', 'counterfactual'];
const AUDIENCE_LEVELS = ['technical', 'business', 'end_user', 'developer'];
const EVIDENCE_TYPES = ['data', 'rule', 'precedent', 'intuition', 'statistical'];

export const ExplanationSynthesizerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'request' | 'trace'>('overview');

  // Explanations / requests / traces
  const [explanations, setExplanations] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [traces, setTraces] = useState<any[]>([]);
  const [selectedExplanationId, setSelectedExplanationId] = useState<string>('');
  const [explanationDetail, setExplanationDetail] = useState<any>(null);
  const [lastGenerated, setLastGenerated] = useState<any>(null);

  // Request form
  const [requestForm, setRequestForm] = useState({
    decision_id: '',
    explanation_type: 'decision',
    audience: 'technical',
    question: '',
    context: '',
  });

  // Generate form
  const [generateForm, setGenerateForm] = useState({
    request_id: '',
  });

  // Trace form
  const [traceForm, setTraceForm] = useState({
    agent_id: '',
    decision_id: '',
    action_taken: '',
    inputs: '',
    reasoning_steps: '',
    alternatives: '',
  });

  // Evidence form
  const [evidenceForm, setEvidenceForm] = useState({
    explanation_id: '',
    evidence_type: 'data',
    content: '',
    source: '',
    weight: '1.0',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.explanationSynthesizer.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load explanation synthesizer stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadExplanations = useCallback(async () => {
    try {
      const result = await api.explanationSynthesizer.listExplanations();
      const list = Array.isArray(result) ? result : (result?.explanations ?? []);
      setExplanations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load explanations');
    }
  }, [toast]);

  const loadRequests = useCallback(async () => {
    try {
      const result = await api.explanationSynthesizer.listRequests();
      const list = Array.isArray(result) ? result : (result?.requests ?? []);
      setRequests(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load requests');
    }
  }, [toast]);

  const loadTraces = useCallback(async () => {
    try {
      const result = await api.explanationSynthesizer.listTraces();
      const list = Array.isArray(result) ? result : (result?.traces ?? []);
      setTraces(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load traces');
    }
  }, [toast]);

  const loadExplanationDetail = useCallback(async (explanationId: string) => {
    if (!explanationId) return;
    try {
      const detail = await api.explanationSynthesizer.getExplanation(explanationId);
      setExplanationDetail(detail);
    } catch (e: any) {
      setExplanationDetail(null);
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadExplanations();
      loadRequests();
      loadTraces();
    }
  }, [activeSection, loadStats, loadExplanations, loadRequests, loadTraces]);

  // When explanation changes, refresh its detail
  useEffect(() => {
    if (selectedExplanationId) {
      loadExplanationDetail(selectedExplanationId);
    }
  }, [selectedExplanationId, loadExplanationDetail]);

  // Auto-select first explanation when entering request section
  useEffect(() => {
    if (activeSection === 'request' && !selectedExplanationId && explanations.length > 0) {
      setSelectedExplanationId(explanations[0].explanation_id ?? explanations[0].id);
    }
  }, [activeSection, selectedExplanationId, explanations]);

  const handleRequestExplanation = async () => {
    if (!requestForm.decision_id.trim()) {
      toast.error('Decision ID is required');
      return;
    }
    try {
      const payload: any = {
        decision_id: requestForm.decision_id.trim(),
        explanation_type: requestForm.explanation_type,
        audience: requestForm.audience,
      };
      if (requestForm.question.trim()) payload.question = requestForm.question.trim();
      if (requestForm.context.trim()) {
        try { payload.context = JSON.parse(requestForm.context); } catch { payload.context = { text: requestForm.context }; }
      }
      const result = await api.explanationSynthesizer.requestExplanation(payload);
      toast.success(`Explanation requested: ${result?.request_id ?? ''}`);
      setGenerateForm({ request_id: result?.request_id ?? '' });
      setRequestForm({ decision_id: '', explanation_type: 'decision', audience: 'technical', question: '', context: '' });
      loadRequests();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGenerateExplanation = async () => {
    if (!generateForm.request_id.trim()) {
      toast.error('Request ID is required');
      return;
    }
    try {
      const result = await api.explanationSynthesizer.generateExplanation(generateForm.request_id.trim());
      setLastGenerated(result);
      toast.success('Explanation generated');
      const newId = result?.explanation_id ?? result?.id;
      if (newId) {
        setSelectedExplanationId(newId);
        setEvidenceForm({ ...evidenceForm, explanation_id: newId });
      }
      loadExplanations();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTraceDecision = async () => {
    if (!traceForm.agent_id.trim() || !traceForm.decision_id.trim() || !traceForm.action_taken.trim()) {
      toast.error('Agent ID, decision ID, and action taken are required');
      return;
    }
    try {
      const payload: any = {
        agent_id: traceForm.agent_id.trim(),
        decision_id: traceForm.decision_id.trim(),
        action_taken: traceForm.action_taken.trim(),
      };
      if (traceForm.inputs.trim()) {
        try { payload.inputs = JSON.parse(traceForm.inputs); } catch { payload.inputs = { text: traceForm.inputs }; }
      }
      if (traceForm.reasoning_steps.trim()) {
        payload.reasoning_steps = traceForm.reasoning_steps.split(',').map(s => s.trim()).filter(Boolean);
      }
      if (traceForm.alternatives.trim()) {
        payload.alternatives = traceForm.alternatives.split(',').map(s => s.trim()).filter(Boolean);
      }
      await api.explanationSynthesizer.traceDecision(payload);
      toast.success('Decision traced');
      setTraceForm({ agent_id: '', decision_id: '', action_taken: '', inputs: '', reasoning_steps: '', alternatives: '' });
      loadTraces();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEvidence = async () => {
    if (!evidenceForm.explanation_id.trim() || !evidenceForm.content.trim()) {
      toast.error('Explanation ID and content are required');
      return;
    }
    try {
      await api.explanationSynthesizer.addEvidence(evidenceForm.explanation_id.trim(), {
        evidence_type: evidenceForm.evidence_type,
        content: evidenceForm.content.trim(),
        source: evidenceForm.source.trim() || undefined,
        weight: Number(evidenceForm.weight),
      });
      toast.success('Evidence added');
      setEvidenceForm({ explanation_id: evidenceForm.explanation_id, evidence_type: 'data', content: '', source: '', weight: '1.0' });
      loadExplanationDetail(evidenceForm.explanation_id.trim());
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>💡 Explanation Synthesizer</h2>
          <p className="panel-subtitle">Request, generate, and trace explanations for agent decisions</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading explanation synthesizer...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💡 Explanation Synthesizer</h2>
        <p className="panel-subtitle">Request, generate, and trace explanations for agent decisions</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_explanations ?? '-'}</span><span className="stat-label">Explanations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_requests ?? '-'}</span><span className="stat-label">Requests</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_traces ?? '-'}</span><span className="stat-label">Traces</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_evidence ?? '-'}</span><span className="stat-label">Evidence</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.pending_requests ?? '-'}</span><span className="stat-label">Pending</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'request', 'trace'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Explanation Synthesizer Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Explanations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_explanations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Requests</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_requests ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Traces</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_traces ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Evidence</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_evidence ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Pending Requests</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.pending_requests ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Explanations</h3>
            <button onClick={() => loadExplanations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {explanations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No explanations recorded. Request one in the Request section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {explanations.slice(0, 10).map((ex: any) => {
                  const id = ex.explanation_id ?? ex.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{ex.decision_id ?? 'unknown'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{ex.explanation_type ?? 'unknown'}]</span></div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>audience: {ex.audience ?? 'unknown'} · {id}</div>
                        </div>
                        <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setActiveSection('request'); setSelectedExplanationId(id); }}>Open</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Request Section */}
      {activeSection === 'request' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Request Explanation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Decision ID *</label>
                <input value={requestForm.decision_id} onChange={e => setRequestForm({ ...requestForm, decision_id: e.target.value })} placeholder="e.g. decision_42" />
              </div>
              <div className="form-group">
                <label>Explanation Type</label>
                <select value={requestForm.explanation_type} onChange={e => setRequestForm({ ...requestForm, explanation_type: e.target.value })}>
                  {EXPLANATION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Audience</label>
                <select value={requestForm.audience} onChange={e => setRequestForm({ ...requestForm, audience: e.target.value })}>
                  {AUDIENCE_LEVELS.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Question</label>
                <input value={requestForm.question} onChange={e => setRequestForm({ ...requestForm, question: e.target.value })} placeholder="Why did the agent choose X?" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Context (JSON)</label>
                <textarea rows={2} value={requestForm.context} onChange={e => setRequestForm({ ...requestForm, context: e.target.value })} placeholder='{"session_id":"s1"}' />
              </div>
            </div>
            <button onClick={handleRequestExplanation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Request Explanation</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Generate Explanation</h3>
            <div style={{ display: 'flex', gap: 12, marginTop: 12, alignItems: 'flex-end' }}>
              <div className="form-group" style={{ flex: '1 1 auto' }}>
                <label>Request ID *</label>
                <input value={generateForm.request_id} onChange={e => setGenerateForm({ ...generateForm, request_id: e.target.value })} placeholder="e.g. req_xxx" list="request-options" />
                <datalist id="request-options">
                  {requests.map((r: any) => <option key={r.request_id ?? r.id} value={r.request_id ?? r.id} />)}
                </datalist>
              </div>
              <button onClick={handleGenerateExplanation} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Generate</button>
            </div>
            {lastGenerated && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(lastGenerated, null, 2)}</pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Explanation Detail</h3>
            <div className="form-group" style={{ marginBottom: 12 }}>
              <label>Explanation ID</label>
              <select
                value={selectedExplanationId}
                onChange={e => { setSelectedExplanationId(e.target.value); setEvidenceForm({ ...evidenceForm, explanation_id: e.target.value }); }}
              >
                <option value="">— Select an explanation —</option>
                {explanations.map((ex: any) => {
                  const id = ex.explanation_id ?? ex.id;
                  return <option key={id} value={id}>{id}</option>;
                })}
              </select>
            </div>
            {explanationDetail && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(explanationDetail, null, 2)}</pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Add Evidence</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Explanation ID *</label>
                <input value={evidenceForm.explanation_id} onChange={e => setEvidenceForm({ ...evidenceForm, explanation_id: e.target.value })} placeholder="e.g. expl_xxx" />
              </div>
              <div className="form-group">
                <label>Evidence Type</label>
                <select value={evidenceForm.evidence_type} onChange={e => setEvidenceForm({ ...evidenceForm, evidence_type: e.target.value })}>
                  {EVIDENCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Source</label>
                <input value={evidenceForm.source} onChange={e => setEvidenceForm({ ...evidenceForm, source: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Weight (0-1)</label>
                <input value={evidenceForm.weight} onChange={e => setEvidenceForm({ ...evidenceForm, weight: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Content *</label>
                <textarea rows={3} value={evidenceForm.content} onChange={e => setEvidenceForm({ ...evidenceForm, content: e.target.value })} />
              </div>
            </div>
            <button onClick={handleAddEvidence} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Evidence</button>
          </div>
        </div>
      )}

      {/* Trace Section */}
      {activeSection === 'trace' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Trace Decision</h3>
            <p style={{ color: themeColors.text, opacity: 0.8, marginTop: 4 }}>Record the reasoning steps behind an agent's decision.</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={traceForm.agent_id} onChange={e => setTraceForm({ ...traceForm, agent_id: e.target.value })} placeholder="e.g. agent_x1" />
              </div>
              <div className="form-group">
                <label>Decision ID *</label>
                <input value={traceForm.decision_id} onChange={e => setTraceForm({ ...traceForm, decision_id: e.target.value })} placeholder="e.g. decision_42" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Action Taken *</label>
                <input value={traceForm.action_taken} onChange={e => setTraceForm({ ...traceForm, action_taken: e.target.value })} placeholder="e.g. route_request_to_team_b" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Inputs (JSON)</label>
                <textarea rows={2} value={traceForm.inputs} onChange={e => setTraceForm({ ...traceForm, inputs: e.target.value })} placeholder='{"priority":"high"}' />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Reasoning Steps (comma-separated)</label>
                <input value={traceForm.reasoning_steps} onChange={e => setTraceForm({ ...traceForm, reasoning_steps: e.target.value })} placeholder="identify_intent, lookup_team, route" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Alternatives (comma-separated)</label>
                <input value={traceForm.alternatives} onChange={e => setTraceForm({ ...traceForm, alternatives: e.target.value })} placeholder="route_to_team_a, escalate" />
              </div>
            </div>
            <button onClick={handleTraceDecision} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Trace Decision</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Traces ({traces.length})</h3>
            <button onClick={() => loadTraces()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {traces.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No traces recorded. Trace a decision above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {traces.slice(0, 20).map((t: any, i: number) => {
                  const id = t.trace_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{t.agent_id ?? 'agent'} / {t.decision_id ?? 'decision'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{t.action_taken ?? 'action'}]</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
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

export default ExplanationSynthesizerPanel;
