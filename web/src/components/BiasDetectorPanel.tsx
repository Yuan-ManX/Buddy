import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: red for bias detector
const themeColors = {
  primary: '#dc2626',
  secondary: '#ef4444',
  bg: '#fef2f2',
  border: '#fecaca',
  accent: '#fee2e2',
  text: '#7f1d1d',
};

// Enum values must match backend BiasType / BiasSeverity / DebiasingStrategy / AuditStatus / EvidenceRole exactly (uppercase).
const BIAS_TYPES = ['CONFIRMATION', 'ANCHORING', 'AVAILABILITY', 'RECENCY', 'SUNK_COST', 'FRAMING', 'REPRESENTATIVENESS', 'OVERCONFIDENCE'];
const BIAS_SEVERITY = ['LOW', 'MODERATE', 'HIGH', 'CRITICAL'];
const DEBIASING_STRATEGIES = ['COUNTERFACTUAL_PROBING', 'PERSPECTIVE_SHIFTING', 'EVIDENCE_DIVERSIFICATION', 'BASE_RATE_RECALIBRATION', 'BLIND_REVIEW', 'DELAYED_JUDGMENT'];
const AUDIT_STATUS = ['PENDING', 'COMPLETED', 'DISPUTED', 'RESOLVED'];
const EVIDENCE_ROLES = ['SUPPORTING', 'CONTRADICTING', 'NEUTRAL'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  PENDING: '#9ca3af',
  COMPLETED: '#059669',
  DISPUTED: '#d97706',
  RESOLVED: '#0d9488',
};

// Map a severity value to a badge color.
const SEVERITY_COLORS: Record<string, string> = {
  LOW: '#9ca3af',
  MODERATE: '#d97706',
  HIGH: '#ea580c',
  CRITICAL: '#dc2626',
};

export const BiasDetectorPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'audit' | 'detection'>('overview');

  // Audits / detections / selected audit
  const [audits, setAudits] = useState<any[]>([]);
  const [detections, setDetections] = useState<any[]>([]);
  const [selectedAudit, setSelectedAudit] = useState<string>('');

  // Reasoning form
  const [reasoningForm, setReasoningForm] = useState({
    agent_id: '',
    reasoning_trace: '',
    context: '',
  });

  // Debiasing form (applied to a detection)
  const [debiasForm, setDebiasForm] = useState({
    detection_id: '',
    strategy: 'COUNTERFACTUAL_PROBING',
  });

  // Resolve form (applied to a detection)
  const [resolveForm, setResolveForm] = useState({
    detection_id: '',
    resolution_note: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.biasDetector.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load bias detector stats');
    } finally {
      setLoading(false);
    }
  };

  const loadAudits = async () => {
    try {
      const result = await api.biasDetector.listAudits();
      const list = Array.isArray(result) ? result : (result?.audits ?? []);
      setAudits(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load audits');
    }
  };

  const loadDetections = async () => {
    if (!selectedAudit) { setDetections([]); return; }
    try {
      const result = await api.biasDetector.listDetections(selectedAudit);
      const list = Array.isArray(result) ? result : (result?.detections ?? []);
      setDetections(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load detections');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadAudits();
    }
  }, [activeSection]);

  // Reload detections when selected audit changes
  useEffect(() => { loadDetections(); }, [selectedAudit]);

  const handleSubmitReasoning = async () => {
    if (!reasoningForm.agent_id.trim() || !reasoningForm.reasoning_trace.trim()) {
      toast.error('Agent ID and reasoning trace are required');
      return;
    }
    const payload: any = {
      agent_id: reasoningForm.agent_id.trim(),
      reasoning_trace: reasoningForm.reasoning_trace.trim(),
    };
    if (reasoningForm.context.trim()) {
      try { payload.context = JSON.parse(reasoningForm.context); }
      catch { toast.error('Context must be valid JSON'); return; }
    }
    try {
      await api.biasDetector.submitReasoning(payload);
      toast.success('Reasoning submitted for audit');
      setReasoningForm({ agent_id: '', reasoning_trace: '', context: '' });
      await loadAudits();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDetectBiases = async (auditId: string) => {
    if (!auditId) { toast.error('Select an audit first'); return; }
    try {
      await api.biasDetector.detectBiases(auditId);
      toast.success('Bias detection triggered');
      if (selectedAudit === auditId) await loadDetections();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyDebiasing = async () => {
    if (!debiasForm.detection_id.trim()) {
      toast.error('Detection ID is required');
      return;
    }
    try {
      await api.biasDetector.applyDebiasing(debiasForm.detection_id.trim(), debiasForm.strategy);
      toast.success('Debiasing strategy applied');
      setDebiasForm({ detection_id: '', strategy: 'COUNTERFACTUAL_PROBING' });
      await loadDetections();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleResolveDetection = async () => {
    if (!resolveForm.detection_id.trim()) {
      toast.error('Detection ID is required');
      return;
    }
    try {
      await api.biasDetector.resolveDetection(resolveForm.detection_id.trim(), resolveForm.resolution_note.trim());
      toast.success('Detection resolved');
      setResolveForm({ detection_id: '', resolution_note: '' });
      await loadDetections();
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
  const severityColor = (s: string) => SEVERITY_COLORS[s] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>⚖️ Bias Detector</h2>
          <p className="panel-subtitle">Audit reasoning traces, detect biases, and apply debiasing strategies</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading bias detector...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚖️ Bias Detector</h2>
        <p className="panel-subtitle">Audit reasoning traces, detect biases, and apply debiasing strategies</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_audits ?? '-'}</span><span className="stat-label">Audits</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_detections ?? '-'}</span><span className="stat-label">Detections</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.pending_count ?? '-'}</span><span className="stat-label">Pending</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.resolved_count ?? '-'}</span><span className="stat-label">Resolved</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_debiasing_actions ?? '-'}</span><span className="stat-label">Actions</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'audit', 'detection'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Bias Detector Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Audits</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_audits ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Detections</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_detections ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Pending</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.pending_count ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Resolved</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.resolved_count ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Debiasing Actions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_debiasing_actions ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Audits</h3>
            <button onClick={() => loadAudits()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {audits.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No audits recorded. Submit reasoning in the Audit section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {audits.slice(0, 10).map((a: any, i: number) => {
                  const id = a.audit_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div>
                          {a.status && renderBadge(a.status, statusColor(a.status))}
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

      {/* Audit Section */}
      {activeSection === 'audit' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Submit Reasoning for Audit</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={reasoningForm.agent_id} onChange={e => setReasoningForm({ ...reasoningForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Reasoning Trace *</label>
                <input value={reasoningForm.reasoning_trace} onChange={e => setReasoningForm({ ...reasoningForm, reasoning_trace: e.target.value })} placeholder="The reasoning trace to audit" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Context (JSON)</label>
                <input value={reasoningForm.context} onChange={e => setReasoningForm({ ...reasoningForm, context: e.target.value })} placeholder='{"domain": "medical"}' />
              </div>
            </div>
            <button onClick={handleSubmitReasoning} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Submit Reasoning</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Audits ({audits.length})</h3>
            <button onClick={() => loadAudits()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {audits.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No audits recorded. Submit reasoning above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {audits.slice(0, 30).map((a: any, i: number) => {
                  const id = a.audit_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.status && renderBadge(a.status, statusColor(a.status))}
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => handleDetectBiases(id)}>Detect</button>
                          <button className="btn-sm" style={{ background: themeColors.secondary, color: '#fff', marginLeft: 4 }} onClick={() => setSelectedAudit(id)}>View Detections</button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {selectedAudit && (
              <div style={{ marginTop: 12, padding: 8, background: themeColors.accent, borderRadius: 6, color: themeColors.text, fontSize: 13 }}>
                Selected audit: <strong>{selectedAudit}</strong>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Detection Section */}
      {activeSection === 'detection' && (
        <div className="dashboard-section">
          <div style={{ padding: 12, background: themeColors.accent, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16, color: themeColors.text }}>
            Selected audit: <strong>{selectedAudit || 'none selected'}</strong> — pick an audit in the Audit section to load its detections.
          </div>

          {/* Apply Debiasing */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Debiasing</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Detection ID *</label>
                <input value={debiasForm.detection_id} onChange={e => setDebiasForm({ ...debiasForm, detection_id: e.target.value })} placeholder="detection id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={debiasForm.strategy} onChange={e => setDebiasForm({ ...debiasForm, strategy: e.target.value })}>
                  {DEBIASING_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleApplyDebiasing} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Debiasing</button>
          </div>

          {/* Resolve Detection */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Resolve Detection</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Detection ID *</label>
                <input value={resolveForm.detection_id} onChange={e => setResolveForm({ ...resolveForm, detection_id: e.target.value })} placeholder="detection id" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Resolution Note</label>
                <input value={resolveForm.resolution_note} onChange={e => setResolveForm({ ...resolveForm, resolution_note: e.target.value })} placeholder="Optional note" />
              </div>
            </div>
            <button onClick={handleResolveDetection} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Resolve Detection</button>
          </div>

          {/* Detections List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Detections ({detections.length})</h3>
            <button onClick={() => loadDetections()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {detections.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No detections recorded for the selected audit.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {detections.slice(0, 30).map((d: any, i: number) => {
                  const id = d.detection_id ?? d.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{d.bias_type ?? 'unknown_bias'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {d.bias_type && renderBadge(d.bias_type, themeColors.secondary)}
                          {d.severity && renderBadge(d.severity, severityColor(d.severity))}
                          {d.status && renderBadge(d.status, statusColor(d.status))}
                        </div>
                      </div>
                      {d.explanation && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.8, marginTop: 6 }}>{d.explanation}</div>
                      )}
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

export default BiasDetectorPanel;
