import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: amber/orange for cognitive workload
const themeColors = {
  primary: '#d97706',
  secondary: '#f59e0b',
  bg: '#fffbeb',
  border: '#fed7aa',
  accent: '#fef3c7',
  text: '#78350f',
};

// Enum values must match backend LoadType / WorkloadState / AllocationStrategy / RecoveryAction exactly (uppercase).
const LOAD_TYPES = ['INTRINSIC', 'EXTRANEOUS', 'GERMANE'];
const WORKLOAD_STATES = ['UNDERLOADED', 'OPTIMAL', 'LOADED', 'OVERLOADED', 'SATURATED', 'RECOVERING'];
const ALLOCATION_STRATEGIES = ['SHED', 'DEFER', 'DELEGATE', 'CHUNK', 'SEQUENCE', 'OFFLOAD'];
const RECOVERY_ACTIONS = ['PAUSE', 'BREATH', 'CONSOLIDATE', 'SIMPLIFY', 'ARCHIVE'];

// Map a workload state value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  UNDERLOADED: '#9ca3af',
  OPTIMAL: '#16a34a',
  LOADED: '#0ea5e9',
  OVERLOADED: '#f59e0b',
  SATURATED: '#dc2626',
  RECOVERING: '#8b5cf6',
};

export const CognitiveWorkloadPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'measurement' | 'allocation'>('overview');

  // Measurements / snapshots / allocations
  const [measurements, setMeasurements] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [interferenceResult, setInterferenceResult] = useState<any>(null);
  const [recoveryResult, setRecoveryResult] = useState<any>(null);

  // Record measurement form
  const [measurementForm, setMeasurementForm] = useState({
    agent_id: '',
    load_type: 'INTRINSIC',
    value: '',
    source_task: '',
    element_complexity: '',
    element_interactivity: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
    active_tasks: '',
  });

  // Assess interference form
  const [interferenceForm, setInterferenceForm] = useState({
    agent_id: '',
    primary_task: '',
    secondary_task: '',
  });

  // Decide allocation form
  const [allocationForm, setAllocationForm] = useState({
    agent_id: '',
    target_task: '',
    current_load: '',
    strategy: 'SHED',
    rationale: '',
  });

  // Create recovery form
  const [recoveryForm, setRecoveryForm] = useState({
    agent_id: '',
    action: 'PAUSE',
    duration_estimate: '',
    expected_relief: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveWorkload.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive workload stats');
    } finally {
      setLoading(false);
    }
  };

  const loadMeasurements = async () => {
    try {
      const result = await api.cognitiveWorkload.listMeasurements();
      const list = Array.isArray(result) ? result : (result?.measurements ?? []);
      setMeasurements(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load measurements');
    }
  };

  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveWorkload.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  const loadAllocations = async () => {
    try {
      const result = await api.cognitiveWorkload.listAllocations();
      const list = Array.isArray(result) ? result : (result?.allocations ?? []);
      setAllocations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load allocations');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadMeasurements();
      loadSnapshots();
      loadAllocations();
    }
  }, [activeSection]);

  const handleRecordMeasurement = async () => {
    if (!measurementForm.agent_id.trim() || !measurementForm.value.trim()) {
      toast.error('Agent ID and value are required');
      return;
    }
    const payload: any = {
      agent_id: measurementForm.agent_id.trim(),
      load_type: measurementForm.load_type,
      value: Number(measurementForm.value),
    };
    if (measurementForm.source_task.trim()) payload.source_task = measurementForm.source_task.trim();
    if (measurementForm.element_complexity.trim()) payload.element_complexity = Number(measurementForm.element_complexity);
    if (measurementForm.element_interactivity.trim()) payload.element_interactivity = Number(measurementForm.element_interactivity);
    try {
      await api.cognitiveWorkload.recordMeasurement(payload);
      toast.success('Measurement recorded');
      setMeasurementForm({ agent_id: '', load_type: 'INTRINSIC', value: '', source_task: '', element_complexity: '', element_interactivity: '' });
      await loadMeasurements();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = { agent_id: snapshotForm.agent_id.trim() };
    if (snapshotForm.active_tasks.trim()) payload.active_tasks = Number(snapshotForm.active_tasks);
    try {
      await api.cognitiveWorkload.takeSnapshot(payload);
      toast.success('Snapshot taken');
      setSnapshotForm({ agent_id: '', active_tasks: '' });
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAssessInterference = async () => {
    if (!interferenceForm.agent_id.trim() || !interferenceForm.primary_task.trim() || !interferenceForm.secondary_task.trim()) {
      toast.error('Agent ID and both tasks are required');
      return;
    }
    const payload: any = {
      agent_id: interferenceForm.agent_id.trim(),
      primary_task: interferenceForm.primary_task.trim(),
      secondary_task: interferenceForm.secondary_task.trim(),
    };
    try {
      const result = await api.cognitiveWorkload.assessInterference(payload);
      setInterferenceResult(result);
      toast.success('Interference assessed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDecideAllocation = async () => {
    if (!allocationForm.agent_id.trim() || !allocationForm.target_task.trim() || !allocationForm.current_load.trim()) {
      toast.error('Agent ID, target task, and current load are required');
      return;
    }
    const payload: any = {
      agent_id: allocationForm.agent_id.trim(),
      target_task: allocationForm.target_task.trim(),
      current_load: Number(allocationForm.current_load),
      strategy: allocationForm.strategy,
    };
    if (allocationForm.rationale.trim()) payload.rationale = allocationForm.rationale.trim();
    try {
      await api.cognitiveWorkload.decideAllocation(payload);
      toast.success('Allocation decided');
      setAllocationForm({ agent_id: '', target_task: '', current_load: '', strategy: 'SHED', rationale: '' });
      await loadAllocations();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateRecovery = async () => {
    if (!recoveryForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: recoveryForm.agent_id.trim(),
      action: recoveryForm.action,
    };
    if (recoveryForm.duration_estimate.trim()) payload.duration_estimate = Number(recoveryForm.duration_estimate);
    if (recoveryForm.expected_relief.trim()) payload.expected_relief = Number(recoveryForm.expected_relief);
    try {
      const result = await api.cognitiveWorkload.createRecovery(payload);
      setRecoveryResult(result);
      toast.success('Recovery created');
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
          <h2>⚖️ Cognitive Workload</h2>
          <p className="panel-subtitle">Measure cognitive load, take snapshots, and decide allocations</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive workload...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚖️ Cognitive Workload</h2>
        <p className="panel-subtitle">Measure cognitive load, take snapshots, and decide allocations</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_assessments ?? '-'}</span><span className="stat-label">Assessments</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_decisions ?? '-'}</span><span className="stat-label">Decisions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_recoveries ?? '-'}</span><span className="stat-label">Recoveries</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_total_load ?? '-'}</span><span className="stat-label">Avg Load</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.overload_events ?? '-'}</span><span className="stat-label">Overloads</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'measurement', 'allocation'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Workload Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Assessments</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_assessments ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Decisions</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_decisions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Recoveries</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_recoveries ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Total Load</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_total_load ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Overload Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.overload_events ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Snapshots</h3>
            <button onClick={() => loadSnapshots()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {snapshots.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No snapshots recorded. Take one in the Measurement section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {snapshots.slice(0, 10).map((s: any, i: number) => {
                  const id = s.snapshot_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>snapshot {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.state && renderBadge(s.state, statusColor(s.state))}
                          {s.active_tasks != null && renderBadge(`tasks: ${s.active_tasks}`, themeColors.secondary)}
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

      {/* Measurement Section */}
      {activeSection === 'measurement' && (
        <div className="dashboard-section">
          {/* Record Measurement */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Measurement</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={measurementForm.agent_id} onChange={e => setMeasurementForm({ ...measurementForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Load Type</label>
                <select value={measurementForm.load_type} onChange={e => setMeasurementForm({ ...measurementForm, load_type: e.target.value })}>
                  {LOAD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Value *</label>
                <input value={measurementForm.value} onChange={e => setMeasurementForm({ ...measurementForm, value: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group">
                <label>Source Task</label>
                <input value={measurementForm.source_task} onChange={e => setMeasurementForm({ ...measurementForm, source_task: e.target.value })} placeholder="optional task id" />
              </div>
              <div className="form-group">
                <label>Element Complexity</label>
                <input value={measurementForm.element_complexity} onChange={e => setMeasurementForm({ ...measurementForm, element_complexity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>Element Interactivity</label>
                <input value={measurementForm.element_interactivity} onChange={e => setMeasurementForm({ ...measurementForm, element_interactivity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.6" />
              </div>
            </div>
            <button onClick={handleRecordMeasurement} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Measurement</button>
          </div>

          {/* Take Snapshot */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Take Snapshot</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={snapshotForm.agent_id} onChange={e => setSnapshotForm({ ...snapshotForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Active Tasks</label>
                <input value={snapshotForm.active_tasks} onChange={e => setSnapshotForm({ ...snapshotForm, active_tasks: e.target.value })} type="number" min="0" placeholder="e.g. 3" />
              </div>
            </div>
            <button onClick={handleTakeSnapshot} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Take Snapshot</button>
          </div>

          {/* Assess Interference */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Assess Interference</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={interferenceForm.agent_id} onChange={e => setInterferenceForm({ ...interferenceForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Primary Task *</label>
                <input value={interferenceForm.primary_task} onChange={e => setInterferenceForm({ ...interferenceForm, primary_task: e.target.value })} placeholder="primary task id" />
              </div>
              <div className="form-group">
                <label>Secondary Task *</label>
                <input value={interferenceForm.secondary_task} onChange={e => setInterferenceForm({ ...interferenceForm, secondary_task: e.target.value })} placeholder="secondary task id" />
              </div>
            </div>
            <button onClick={handleAssessInterference} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Assess Interference</button>
            {interferenceResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(interferenceResult, null, 2)}</pre>
            )}
          </div>

          {/* Measurements List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Measurements ({measurements.length})</h3>
            <button onClick={() => loadMeasurements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {measurements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No measurements recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {measurements.slice(0, 30).map((m: any, i: number) => {
                  const id = m.measurement_id ?? m.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {m.agent_id ?? '-'} · value: {m.value ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>measurement {id}{m.source_task ? ` · task: ${m.source_task}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {m.load_type && renderBadge(m.load_type, themeColors.secondary)}
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

      {/* Allocation Section */}
      {activeSection === 'allocation' && (
        <div className="dashboard-section">
          {/* Decide Allocation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Decide Allocation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={allocationForm.agent_id} onChange={e => setAllocationForm({ ...allocationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Target Task *</label>
                <input value={allocationForm.target_task} onChange={e => setAllocationForm({ ...allocationForm, target_task: e.target.value })} placeholder="task id" />
              </div>
              <div className="form-group">
                <label>Current Load *</label>
                <input value={allocationForm.current_load} onChange={e => setAllocationForm({ ...allocationForm, current_load: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.85" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={allocationForm.strategy} onChange={e => setAllocationForm({ ...allocationForm, strategy: e.target.value })}>
                  {ALLOCATION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input value={allocationForm.rationale} onChange={e => setAllocationForm({ ...allocationForm, rationale: e.target.value })} placeholder="optional rationale" />
              </div>
            </div>
            <button onClick={handleDecideAllocation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Decide Allocation</button>
          </div>

          {/* Create Recovery */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Recovery</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={recoveryForm.agent_id} onChange={e => setRecoveryForm({ ...recoveryForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Action</label>
                <select value={recoveryForm.action} onChange={e => setRecoveryForm({ ...recoveryForm, action: e.target.value })}>
                  {RECOVERY_ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Duration Estimate</label>
                <input value={recoveryForm.duration_estimate} onChange={e => setRecoveryForm({ ...recoveryForm, duration_estimate: e.target.value })} type="number" step="0.01" placeholder="e.g. 120" />
              </div>
              <div className="form-group">
                <label>Expected Relief</label>
                <input value={recoveryForm.expected_relief} onChange={e => setRecoveryForm({ ...recoveryForm, expected_relief: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
            </div>
            <button onClick={handleCreateRecovery} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Recovery</button>
            {recoveryResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(recoveryResult, null, 2)}</pre>
            )}
          </div>

          {/* Allocations List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Allocations ({allocations.length})</h3>
            <button onClick={() => loadAllocations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {allocations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No allocations recorded. Decide one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {allocations.slice(0, 30).map((a: any, i: number) => {
                  const id = a.decision_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'} · task: {a.target_task ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>allocation {id} · load: {a.current_load ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.strategy && renderBadge(a.strategy, themeColors.primary)}
                        </div>
                      </div>
                      {a.rationale && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{a.rationale}</div>
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

export default CognitiveWorkloadPanel;
