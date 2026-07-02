import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: red for cognitive immunity
const themeColors = {
  primary: '#dc2626',
  secondary: '#ef4444',
  bg: '#fef2f2',
  border: '#fecaca',
  accent: '#fee2e2',
  text: '#7f1d1d',
};

// Enum values must match backend ThreatType / ImmuneResponse / ImmunityRegime / ToleranceLevel / MemoryState exactly (uppercase).
const THREAT_TYPES = ['CONTRADICTION', 'MANIPULATION', 'MISINFORMATION', 'COGNITIVE_OVERLOAD', 'PARASITIC', 'CORRUPTION', 'ALIEN'];
const IMMUNE_RESPONSES = ['IGNORE', 'FLAG', 'QUARANTINE', 'NEUTRALIZE', 'REJECT', 'ASSIMILATE'];
const IMMUNITY_REGIMES = ['COMPROMISED', 'SLUGGISH', 'VIGILANT', 'HYPERACTIVE', 'ROBUST'];
const TOLERANCE_LEVELS = ['NONE', 'LOW', 'MODERATE', 'HIGH', 'AUTO_IMMUNE'];
const MEMORY_STATES = ['NAIVE', 'PRIMED', 'ACTIVE', 'MEMORY', 'EXHAUSTED'];

// Map an immunity regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  COMPROMISED: '#dc2626',
  SLUGGISH: '#f97316',
  VIGILANT: '#0ea5e9',
  HYPERACTIVE: '#e11d48',
  ROBUST: '#16a34a',
};

export const CognitiveImmunityPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'detection' | 'response' | 'memory'>('overview');

  // Detections / responses / memories
  const [detections, setDetections] = useState<any[]>([]);
  const [responses, setResponses] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Detect threat form
  const [detectForm, setDetectForm] = useState({
    agent_id: '',
    threat_type: 'CONTRADICTION',
    source: '',
    severity: '',
    evidence: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Assess tolerance form
  const [toleranceForm, setToleranceForm] = useState({
    agent_id: '',
    level: 'NONE',
    false_positive_rate: '',
    self_attack_rate: '',
    rationale: '',
  });

  // Mount response form
  const [responseForm, setResponseForm] = useState({
    agent_id: '',
    detection_id: '',
    response: 'IGNORE',
    rationale: '',
    neutralization_method: '',
    success: true,
  });

  // Record memory form
  const [memoryForm, setMemoryForm] = useState({
    agent_id: '',
    threat_type: 'CONTRADICTION',
    state: 'PRIMED',
    encounter_count: '1',
    last_response: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveImmunity.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive immunity stats');
    } finally {
      setLoading(false);
    }
  };

  const loadDetections = async () => {
    try {
      const result = await api.cognitiveImmunity.listDetections();
      const list = Array.isArray(result) ? result : (result?.detections ?? []);
      setDetections(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load detections');
    }
  };

  const loadResponses = async () => {
    try {
      const result = await api.cognitiveImmunity.listResponses();
      const list = Array.isArray(result) ? result : (result?.responses ?? []);
      setResponses(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load responses');
    }
  };

  const loadMemories = async () => {
    try {
      const result = await api.cognitiveImmunity.listMemories();
      const list = Array.isArray(result) ? result : (result?.memories ?? []);
      setMemories(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load memories');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadDetections();
      loadResponses();
      loadMemories();
    }
  }, [activeSection]);

  const handleDetectThreat = async () => {
    if (!detectForm.agent_id.trim() || !detectForm.source.trim()) {
      toast.error('Agent ID and source are required');
      return;
    }
    const payload: any = {
      agent_id: detectForm.agent_id.trim(),
      threat_type: detectForm.threat_type,
      source: detectForm.source.trim(),
      severity: detectForm.severity.trim() === '' ? 0.5 : Number(detectForm.severity),
      evidence: detectForm.evidence.trim(),
    };
    try {
      await api.cognitiveImmunity.detectThreat(payload);
      toast.success('Threat detected');
      setDetectForm({ agent_id: '', threat_type: 'CONTRADICTION', source: '', severity: '', evidence: '' });
      await loadDetections();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: snapshotForm.agent_id.trim(),
    };
    try {
      const result = await api.cognitiveImmunity.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAssessTolerance = async () => {
    if (!toleranceForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: toleranceForm.agent_id.trim(),
      level: toleranceForm.level,
      false_positive_rate: toleranceForm.false_positive_rate.trim() === '' ? 0 : Number(toleranceForm.false_positive_rate),
      self_attack_rate: toleranceForm.self_attack_rate.trim() === '' ? 0 : Number(toleranceForm.self_attack_rate),
      rationale: toleranceForm.rationale.trim(),
    };
    try {
      await api.cognitiveImmunity.assessTolerance(payload);
      toast.success('Tolerance assessed');
      setToleranceForm({ agent_id: '', level: 'NONE', false_positive_rate: '', self_attack_rate: '', rationale: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMountResponse = async () => {
    if (!responseForm.agent_id.trim() || !responseForm.detection_id.trim()) {
      toast.error('Agent ID and detection ID are required');
      return;
    }
    const payload: any = {
      agent_id: responseForm.agent_id.trim(),
      detection_id: responseForm.detection_id.trim(),
      response: responseForm.response,
      rationale: responseForm.rationale.trim(),
      neutralization_method: responseForm.neutralization_method.trim(),
      success: responseForm.success,
    };
    try {
      await api.cognitiveImmunity.respond(payload);
      toast.success('Response mounted');
      setResponseForm({ agent_id: '', detection_id: '', response: 'IGNORE', rationale: '', neutralization_method: '', success: true });
      await loadResponses();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordMemory = async () => {
    if (!memoryForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: memoryForm.agent_id.trim(),
      threat_type: memoryForm.threat_type,
      state: memoryForm.state,
      encounter_count: memoryForm.encounter_count.trim() === '' ? 1 : Number(memoryForm.encounter_count),
    };
    if (memoryForm.last_response) payload.last_response = memoryForm.last_response;
    try {
      await api.cognitiveImmunity.recordMemory(payload);
      toast.success('Memory recorded');
      setMemoryForm({ agent_id: '', threat_type: 'CONTRADICTION', state: 'PRIMED', encounter_count: '1', last_response: '' });
      await loadMemories();
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
          <h2>🛡️ Cognitive Immunity</h2>
          <p className="panel-subtitle">Detect threats, mount immune responses, and track tolerance across the cognitive defense system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive immunity...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🛡️ Cognitive Immunity</h2>
        <p className="panel-subtitle">Detect threats, mount immune responses, and track tolerance across the cognitive defense system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_detections ?? '-'}</span><span className="stat-label">Detections</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_actions ?? '-'}</span><span className="stat-label">Actions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_tolerances ?? '-'}</span><span className="stat-label">Tolerances</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_memories ?? '-'}</span><span className="stat-label">Memories</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_severity ?? '-'}</span><span className="stat-label">Avg Severity</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'detection', 'response', 'memory'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Immunity Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Detections</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_detections ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Actions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_actions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Tolerances</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_tolerances ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Memories</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_memories ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Severity</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_severity ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Detections</h3>
            <button onClick={() => loadDetections()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {detections.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No threats detected. Detect one in the Detection section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {detections.slice(0, 10).map((d: any, i: number) => {
                  const id = d.detection_id ?? d.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {d.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>detection {id}{d.source ? ` · ${d.source}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {d.threat_type && renderBadge(d.threat_type, themeColors.secondary)}
                          {typeof d.severity !== 'undefined' && renderBadge(`severity ${d.severity}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Responses</h3>
            <button onClick={() => loadResponses()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {responses.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No responses mounted. Mount one in the Response section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {responses.slice(0, 10).map((r: any, i: number) => {
                  const id = r.action_id ?? r.response_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>response {id}{r.detection_id ? ` · detection: ${r.detection_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.response && renderBadge(r.response, themeColors.secondary)}
                          {typeof r.success === 'boolean' && renderBadge(r.success ? 'success' : 'failed', r.success ? '#16a34a' : '#dc2626')}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Memories</h3>
            <button onClick={() => loadMemories()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {memories.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No memories recorded. Record one in the Memory section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {memories.slice(0, 10).map((m: any, i: number) => {
                  const id = m.memory_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>memory {id}{m.threat_type ? ` · ${m.threat_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.threat_type && renderBadge(m.threat_type, themeColors.secondary)}
                          {m.state && renderBadge(m.state, statusColor(m.state))}
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

      {/* Detection Section */}
      {activeSection === 'detection' && (
        <div className="dashboard-section">
          {/* Detect Threat */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Detect Threat</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={detectForm.agent_id} onChange={e => setDetectForm({ ...detectForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Threat Type</label>
                <select className="form-select" value={detectForm.threat_type} onChange={e => setDetectForm({ ...detectForm, threat_type: e.target.value })}>
                  {THREAT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Severity</label>
                <input className="form-input" value={detectForm.severity} onChange={e => setDetectForm({ ...detectForm, severity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Source *</label>
                <input className="form-input" value={detectForm.source} onChange={e => setDetectForm({ ...detectForm, source: e.target.value })} placeholder="threat source" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Evidence</label>
                <input className="form-input" value={detectForm.evidence} onChange={e => setDetectForm({ ...detectForm, evidence: e.target.value })} placeholder="supporting evidence" />
              </div>
            </div>
            <button onClick={handleDetectThreat} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Detect Threat</button>
          </div>

          {/* Take Snapshot */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Take Snapshot</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={snapshotForm.agent_id} onChange={e => setSnapshotForm({ ...snapshotForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
            </div>
            <button onClick={handleTakeSnapshot} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Take Snapshot</button>
            {snapshotResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(snapshotResult, null, 2)}</pre>
            )}
          </div>

          {/* Assess Tolerance */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Assess Tolerance</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={toleranceForm.agent_id} onChange={e => setToleranceForm({ ...toleranceForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Level</label>
                <select className="form-select" value={toleranceForm.level} onChange={e => setToleranceForm({ ...toleranceForm, level: e.target.value })}>
                  {TOLERANCE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>False Positive Rate</label>
                <input className="form-input" value={toleranceForm.false_positive_rate} onChange={e => setToleranceForm({ ...toleranceForm, false_positive_rate: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.1" />
              </div>
              <div className="form-group">
                <label>Self Attack Rate</label>
                <input className="form-input" value={toleranceForm.self_attack_rate} onChange={e => setToleranceForm({ ...toleranceForm, self_attack_rate: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.05" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={toleranceForm.rationale} onChange={e => setToleranceForm({ ...toleranceForm, rationale: e.target.value })} placeholder="rationale for tolerance level" />
              </div>
            </div>
            <button onClick={handleAssessTolerance} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Assess Tolerance</button>
          </div>
        </div>
      )}

      {/* Response Section */}
      {activeSection === 'response' && (
        <div className="dashboard-section">
          {/* Mount Response */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Mount Response</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={responseForm.agent_id} onChange={e => setResponseForm({ ...responseForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Detection ID *</label>
                <input className="form-input" value={responseForm.detection_id} onChange={e => setResponseForm({ ...responseForm, detection_id: e.target.value })} placeholder="detection id" />
              </div>
              <div className="form-group">
                <label>Response</label>
                <select className="form-select" value={responseForm.response} onChange={e => setResponseForm({ ...responseForm, response: e.target.value })}>
                  {IMMUNE_RESPONSES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Neutralization Method</label>
                <input className="form-input" value={responseForm.neutralization_method} onChange={e => setResponseForm({ ...responseForm, neutralization_method: e.target.value })} placeholder="e.g. counter-argument" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={responseForm.rationale} onChange={e => setResponseForm({ ...responseForm, rationale: e.target.value })} placeholder="rationale for response" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input type="checkbox" checked={responseForm.success} onChange={e => setResponseForm({ ...responseForm, success: e.target.checked })} />
                  <span>Success</span>
                </label>
              </div>
            </div>
            <button onClick={handleMountResponse} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Mount Response</button>
          </div>

          {/* Responses List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Responses ({responses.length})</h3>
            <button onClick={() => loadResponses()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {responses.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No responses mounted. Mount one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {responses.slice(0, 30).map((r: any, i: number) => {
                  const id = r.action_id ?? r.response_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>response {id}{r.detection_id ? ` · detection: ${r.detection_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.response && renderBadge(r.response, themeColors.secondary)}
                          {typeof r.success === 'boolean' && renderBadge(r.success ? 'success' : 'failed', r.success ? '#16a34a' : '#dc2626')}
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

      {/* Memory Section */}
      {activeSection === 'memory' && (
        <div className="dashboard-section">
          {/* Record Memory */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Memory</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={memoryForm.agent_id} onChange={e => setMemoryForm({ ...memoryForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Threat Type</label>
                <select className="form-select" value={memoryForm.threat_type} onChange={e => setMemoryForm({ ...memoryForm, threat_type: e.target.value })}>
                  {THREAT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>State</label>
                <select className="form-select" value={memoryForm.state} onChange={e => setMemoryForm({ ...memoryForm, state: e.target.value })}>
                  {MEMORY_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Encounter Count</label>
                <input className="form-input" value={memoryForm.encounter_count} onChange={e => setMemoryForm({ ...memoryForm, encounter_count: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 1" />
              </div>
              <div className="form-group">
                <label>Last Response</label>
                <select className="form-select" value={memoryForm.last_response} onChange={e => setMemoryForm({ ...memoryForm, last_response: e.target.value })}>
                  <option value="">(none)</option>
                  {IMMUNE_RESPONSES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRecordMemory} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Memory</button>
          </div>

          {/* Memories List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Memories ({memories.length})</h3>
            <button onClick={() => loadMemories()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {memories.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No memories recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {memories.slice(0, 30).map((m: any, i: number) => {
                  const id = m.memory_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>memory {id}{m.threat_type ? ` · ${m.threat_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.threat_type && renderBadge(m.threat_type, themeColors.secondary)}
                          {m.state && renderBadge(m.state, statusColor(m.state))}
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

export default CognitiveImmunityPanel;
