import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: red/rose for anomaly detection
const themeColors = {
  primary: '#ef4444',
  secondary: '#f87171',
  bg: '#fef2f2',
  border: '#fecaca',
  accent: '#fee2e2',
  text: '#7f1d1d',
};

// Enum values must match backend MetricDirection / DiagnosisStatus exactly (lowercase).
const METRIC_DIRECTIONS = ['increase', 'decrease', 'bidirectional'];
const DIAGNOSIS_STATUSES = ['pending', 'investigating', 'identified', 'resolved', 'unresolved'];
const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  error: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
};

export const AnomalyDetectorPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'baseline' | 'observe' | 'diagnose'>('overview');

  // Baselines / metrics / anomalies
  const [baselines, setBaselines] = useState<any[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [baselineDetail, setBaselineDetail] = useState<any>(null);
  const [baselineSummary, setBaselineSummary] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [driftReport, setDriftReport] = useState<any>(null);

  // Baseline form
  const [baselineForm, setBaselineForm] = useState({
    agent_id: '',
    sample_window: '100',
    min_samples: '30',
  });

  // Metric form
  const [metricForm, setMetricForm] = useState({
    name: '',
    description: '',
    direction: 'bidirectional',
    unit: '',
  });

  // Observation form
  const [obsForm, setObsForm] = useState({
    metric_name: '',
    value: '',
    context: '',
  });
  const [lastObservation, setLastObservation] = useState<any>(null);

  // Drift form
  const [driftWindow, setDriftWindow] = useState('20');

  // Diagnosis form
  const [diagForm, setDiagForm] = useState({
    diagnosis_id: '',
    root_cause: '',
    contributing_factors: '',
    recommended_actions: '',
    confidence: '0.5',
    status: 'investigating',
  });
  const [diagResolveForm, setDiagResolveForm] = useState({ diagnosis_id: '', resolution: '' });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.anomalyDetector.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load anomaly detector stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBaselines = useCallback(async () => {
    try {
      const result = await api.anomalyDetector.listBaselines();
      const list = Array.isArray(result) ? result : (result?.baselines ?? []);
      setBaselines(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load baselines');
    }
  }, [toast]);

  const loadBaselineDetail = useCallback(async (agentId: string) => {
    if (!agentId) return;
    try {
      const detail = await api.anomalyDetector.getBaseline(agentId);
      setBaselineDetail(detail);
      const summary = await api.anomalyDetector.baselineSummary(agentId).catch(() => null);
      setBaselineSummary(summary);
    } catch (e: any) {
      // 404 is okay; baseline may not exist yet
      setBaselineDetail(null);
      setBaselineSummary(null);
    }
  }, []);

  const loadAnomalies = useCallback(async (agentId?: string) => {
    try {
      const result = await api.anomalyDetector.listAnomalies(agentId ? { agent_id: agentId, limit: 50 } : { limit: 50 });
      const list = Array.isArray(result) ? result : (result?.anomalies ?? []);
      setAnomalies(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load anomalies');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + baselines when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadBaselines();
      loadAnomalies();
    }
  }, [activeSection, loadStats, loadBaselines, loadAnomalies]);

  // When agent changes, refresh its baseline + anomalies
  useEffect(() => {
    if (selectedAgentId) {
      loadBaselineDetail(selectedAgentId);
      loadAnomalies(selectedAgentId);
    }
  }, [selectedAgentId, loadBaselineDetail, loadAnomalies]);

  // Auto-select first baseline when entering non-overview sections
  useEffect(() => {
    if (activeSection !== 'overview' && !selectedAgentId && baselines.length > 0) {
      setSelectedAgentId(baselines[0].agent_id);
    }
  }, [activeSection, selectedAgentId, baselines]);

  const handleCreateBaseline = async () => {
    if (!baselineForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      await api.anomalyDetector.createBaseline({
        agent_id: baselineForm.agent_id.trim(),
        sample_window: Number(baselineForm.sample_window),
        min_samples: Number(baselineForm.min_samples),
      });
      toast.success('Baseline created');
      setBaselineForm({ agent_id: '', sample_window: '100', min_samples: '30' });
      await loadBaselines();
      setSelectedAgentId(baselineForm.agent_id.trim());
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRegisterMetric = async () => {
    if (!selectedAgentId || !metricForm.name.trim()) {
      toast.error('Agent and metric name are required');
      return;
    }
    try {
      await api.anomalyDetector.registerMetric(selectedAgentId, {
        name: metricForm.name.trim(),
        description: metricForm.description.trim() || undefined,
        direction: metricForm.direction,
        unit: metricForm.unit.trim() || undefined,
      });
      toast.success('Metric registered');
      setMetricForm({ name: '', description: '', direction: 'bidirectional', unit: '' });
      loadBaselineDetail(selectedAgentId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleObserve = async () => {
    if (!selectedAgentId || !obsForm.metric_name.trim() || obsForm.value.trim() === '') {
      toast.error('Agent, metric, and value are required');
      return;
    }
    try {
      let context: any = {};
      if (obsForm.context.trim()) {
        try { context = JSON.parse(obsForm.context); } catch { context = { text: obsForm.context }; }
      }
      const result = await api.anomalyDetector.recordObservation(selectedAgentId, {
        metric_name: obsForm.metric_name.trim(),
        value: Number(obsForm.value),
        context,
      });
      setLastObservation(result);
      if (result?.anomaly_detected) {
        toast.error(`Anomaly detected: ${result.anomaly?.severity ?? 'unknown'}`);
      } else {
        toast.success('Observation recorded (within normal range)');
      }
      setObsForm({ metric_name: '', value: '', context: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDetectDrift = async () => {
    if (!selectedAgentId) return;
    try {
      const result = await api.anomalyDetector.detectDrift(selectedAgentId, Number(driftWindow));
      setDriftReport(result);
      if (result?.drift_detected) {
        toast.error('Behavioral drift detected');
      } else {
        toast.success('No drift detected');
      }
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAcknowledge = async (anomalyId: string) => {
    try {
      await api.anomalyDetector.acknowledge(anomalyId);
      toast.success('Anomaly acknowledged');
      if (selectedAgentId) loadAnomalies(selectedAgentId); else loadAnomalies();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleResolve = async (anomalyId: string) => {
    try {
      await api.anomalyDetector.resolve(anomalyId);
      toast.success('Anomaly resolved');
      if (selectedAgentId) loadAnomalies(selectedAgentId); else loadAnomalies();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleStartDiagnosis = async (anomalyId: string) => {
    try {
      const report = await api.anomalyDetector.startDiagnosis(anomalyId);
      toast.success(`Diagnosis started: ${report?.diagnosis_id ?? ''}`);
      setDiagForm({ ...diagForm, diagnosis_id: report?.diagnosis_id ?? '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleUpdateDiagnosis = async () => {
    if (!diagForm.diagnosis_id.trim()) {
      toast.error('Diagnosis ID required');
      return;
    }
    try {
      const factors = diagForm.contributing_factors.split(',').map(s => s.trim()).filter(Boolean);
      const actions = diagForm.recommended_actions.split(',').map(s => s.trim()).filter(Boolean);
      await api.anomalyDetector.updateDiagnosis(diagForm.diagnosis_id.trim(), {
        root_cause: diagForm.root_cause.trim() || undefined,
        contributing_factors: factors,
        recommended_actions: actions,
        confidence: Number(diagForm.confidence),
        status: diagForm.status,
      });
      toast.success('Diagnosis updated');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleResolveDiagnosis = async () => {
    if (!diagResolveForm.diagnosis_id.trim()) {
      toast.error('Diagnosis ID required');
      return;
    }
    try {
      await api.anomalyDetector.resolveDiagnosis(diagResolveForm.diagnosis_id.trim(), diagResolveForm.resolution.trim() || undefined);
      toast.success('Diagnosis resolved');
      setDiagResolveForm({ diagnosis_id: '', resolution: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🚨 Anomaly Detector</h2>
          <p className="panel-subtitle">Behavior baselines, drift detection, and self-diagnosis</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading anomaly detector...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🚨 Anomaly Detector</h2>
        <p className="panel-subtitle">Behavior baselines, drift detection, and self-diagnosis</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_baselines ?? '-'}</span><span className="stat-label">Baselines</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_anomalies ?? '-'}</span><span className="stat-label">Anomalies</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.unresolved_anomalies ?? '-'}</span><span className="stat-label">Open</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.critical_anomalies ?? '-'}</span><span className="stat-label">Critical</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_diagnoses ?? '-'}</span><span className="stat-label">Diagnoses</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'baseline', 'observe', 'diagnose'] as const).map(s => (
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

      {/* Agent selector shared across non-overview sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Agent Baseline</label>
          <select
            value={selectedAgentId}
            onChange={e => { setSelectedAgentId(e.target.value); setDriftReport(null); setLastObservation(null); }}
          >
            <option value="">— Select an agent —</option>
            {baselines.map((b: any) => (
              <option key={b.agent_id} value={b.agent_id}>{b.agent_id}</option>
            ))}
          </select>
        </div>
      )}

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Anomaly Detector Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Baselines</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_baselines ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Anomalies</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_anomalies ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Unresolved</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.unresolved_anomalies ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Critical</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.critical_anomalies ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Diagnoses</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_diagnoses ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Drift Reports</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_drift_reports ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Anomalies</h3>
            <button onClick={() => loadAnomalies()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {anomalies.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No anomalies recorded. Create a baseline and observe metrics.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {anomalies.slice(0, 10).map((a: any) => {
                  const id = a.anomaly_id ?? a.id;
                  const sev = a.severity ?? 'info';
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${SEVERITY_COLORS[sev] ?? themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{a.metric_name ?? 'unknown'} <span style={{ color: SEVERITY_COLORS[sev] ?? themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{sev}]</span></div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{a.agent_id} · z-score {a.z_score?.toFixed?.(2) ?? a.z_score} · {id}</div>
                        </div>
                        <div style={{ fontSize: 12, color: a.resolved ? '#10b981' : '#f59e0b' }}>{a.resolved ? 'resolved' : (a.acknowledged ? 'acked' : 'open')}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Baseline Section */}
      {activeSection === 'baseline' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Behavior Baseline</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={baselineForm.agent_id} onChange={e => setBaselineForm({ ...baselineForm, agent_id: e.target.value })} placeholder="e.g. agent_x1" />
              </div>
              <div className="form-group">
                <label>Sample Window</label>
                <input value={baselineForm.sample_window} onChange={e => setBaselineForm({ ...baselineForm, sample_window: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Min Samples</label>
                <input value={baselineForm.min_samples} onChange={e => setBaselineForm({ ...baselineForm, min_samples: e.target.value })} type="number" />
              </div>
            </div>
            <button onClick={handleCreateBaseline} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Baseline</button>
          </div>

          {selectedAgentId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Register Metric</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Metric Name *</label>
                    <input value={metricForm.name} onChange={e => setMetricForm({ ...metricForm, name: e.target.value })} placeholder="e.g. response_latency_ms" />
                  </div>
                  <div className="form-group">
                    <label>Direction</label>
                    <select value={metricForm.direction} onChange={e => setMetricForm({ ...metricForm, direction: e.target.value })}>
                      {METRIC_DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Unit</label>
                    <input value={metricForm.unit} onChange={e => setMetricForm({ ...metricForm, unit: e.target.value })} placeholder="ms, count, etc." />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={metricForm.description} onChange={e => setMetricForm({ ...metricForm, description: e.target.value })} />
                  </div>
                </div>
                <button onClick={handleRegisterMetric} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Metric</button>
              </div>

              {baselineDetail && (
                <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                  <h3 style={{ color: themeColors.text }}>Baseline: {selectedAgentId}</h3>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(baselineDetail, null, 2)}</pre>
                  {baselineSummary && (
                    <>
                      <h4 style={{ color: themeColors.text, marginTop: 16 }}>Summary</h4>
                      <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(baselineSummary, null, 2)}</pre>
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Observe Section */}
      {activeSection === 'observe' && selectedAgentId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Observation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Metric Name *</label>
                <input value={obsForm.metric_name} onChange={e => setObsForm({ ...obsForm, metric_name: e.target.value })} placeholder="e.g. response_latency_ms" list="metric-options" />
                <datalist id="metric-options">
                  {(baselineDetail?.metrics ?? []).map((m: any) => <option key={m.name} value={m.name} />)}
                </datalist>
              </div>
              <div className="form-group">
                <label>Value *</label>
                <input value={obsForm.value} onChange={e => setObsForm({ ...obsForm, value: e.target.value })} type="number" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Context (JSON)</label>
                <textarea rows={2} value={obsForm.context} onChange={e => setObsForm({ ...obsForm, context: e.target.value })} placeholder='{"endpoint":"/chat"}' />
              </div>
            </div>
            <button onClick={handleObserve} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Observation</button>
          </div>

          {lastObservation && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Last Observation Result</h3>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(lastObservation, null, 2)}</pre>
            </div>
          )}

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Drift Detection</h3>
            <div style={{ display: 'flex', gap: 12, marginTop: 12, alignItems: 'flex-end' }}>
              <div className="form-group" style={{ flex: '0 0 200px' }}>
                <label>Window Size</label>
                <input value={driftWindow} onChange={e => setDriftWindow(e.target.value)} type="number" />
              </div>
              <button onClick={handleDetectDrift} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Detect Drift</button>
            </div>
            {driftReport && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(driftReport, null, 2)}</pre>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Anomalies for {selectedAgentId} ({anomalies.length})</h3>
            <button onClick={() => loadAnomalies(selectedAgentId)} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {anomalies.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No anomalies recorded for this agent.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {anomalies.map((a: any) => {
                  const id = a.anomaly_id ?? a.id;
                  const sev = a.severity ?? 'info';
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${SEVERITY_COLORS[sev] ?? themeColors.primary}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{a.metric_name} <span style={{ color: SEVERITY_COLORS[sev] ?? themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{sev}]</span></div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>value {String(a.observed_value)} · z {a.z_score?.toFixed?.(2) ?? a.z_score} · {id}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {!a.acknowledged && !a.resolved && (
                          <button className="btn-sm" style={{ background: '#f59e0b', color: '#fff' }} onClick={() => handleAcknowledge(id)}>Ack</button>
                        )}
                        {!a.resolved && (
                          <button className="btn-sm" style={{ background: '#10b981', color: '#fff' }} onClick={() => handleResolve(id)}>Resolve</button>
                        )}
                        <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => handleStartDiagnosis(id)}>Diagnose</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Diagnose Section */}
      {activeSection === 'diagnose' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Update Diagnosis</h3>
            <p style={{ color: themeColors.text, opacity: 0.8, marginTop: 4 }}>Start a diagnosis from the Observe section, then update its findings here.</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Diagnosis ID *</label>
                <input value={diagForm.diagnosis_id} onChange={e => setDiagForm({ ...diagForm, diagnosis_id: e.target.value })} placeholder="e.g. diag_xxx" />
              </div>
              <div className="form-group">
                <label>Status</label>
                <select value={diagForm.status} onChange={e => setDiagForm({ ...diagForm, status: e.target.value })}>
                  {DIAGNOSIS_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Confidence (0-1)</label>
                <input value={diagForm.confidence} onChange={e => setDiagForm({ ...diagForm, confidence: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Root Cause</label>
                <input value={diagForm.root_cause} onChange={e => setDiagForm({ ...diagForm, root_cause: e.target.value })} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Contributing Factors (comma-separated)</label>
                <input value={diagForm.contributing_factors} onChange={e => setDiagForm({ ...diagForm, contributing_factors: e.target.value })} placeholder="cache_miss, high_load" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Recommended Actions (comma-separated)</label>
                <input value={diagForm.recommended_actions} onChange={e => setDiagForm({ ...diagForm, recommended_actions: e.target.value })} placeholder="scale_up, flush_cache" />
              </div>
            </div>
            <button onClick={handleUpdateDiagnosis} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Update Diagnosis</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Resolve Diagnosis</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: 12, marginTop: 12, alignItems: 'flex-end' }}>
              <div className="form-group">
                <label>Diagnosis ID *</label>
                <input value={diagResolveForm.diagnosis_id} onChange={e => setDiagResolveForm({ ...diagResolveForm, diagnosis_id: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Resolution</label>
                <input value={diagResolveForm.resolution} onChange={e => setDiagResolveForm({ ...diagResolveForm, resolution: e.target.value })} placeholder="What was done to resolve" />
              </div>
              <button onClick={handleResolveDiagnosis} className="btn-primary" style={{ background: '#10b981', color: '#fff' }}>Resolve</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnomalyDetectorPanel;
