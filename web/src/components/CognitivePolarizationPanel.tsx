import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: purple for cognitive polarization
const themeColors = {
  primary: '#9333ea',
  secondary: '#a855f7',
  bg: '#faf5ff',
  border: '#e9d5ff',
  accent: '#f3e8ff',
  text: '#581c87',
};

// Enum values must match backend PolarizationAxis / PolarizationRegime / AlignmentState / FilteringStrategy / CoherenceLoss exactly (uppercase).
const POLARIZATION_AXES = ['GOAL', 'EVIDENCE', 'VALUE', 'INTENT', 'AUTHORITY', 'EMOTION'];
const POLARIZATION_REGIMES = ['COHERENT', 'PARTIAL', 'SPLIT', 'CROSS', 'DEPOLARIZED', 'SCRAMBLED'];
const ALIGNMENT_STATES = ['PARALLEL', 'CONVERGENT', 'DIVERGENT', 'ORTHOGONAL', 'ANTI_PARALLEL', 'RANDOM'];
const FILTERING_STRATEGIES = ['ALIGN', 'CROSS_FILTER', 'ROTATE', 'DEPOLARIZE', 'RECONSTRUCT', 'RESOLVE'];
const COHERENCE_LOSSES = ['NONE', 'MILD', 'MODERATE', 'SEVERE', 'COMPLETE'];

// Map a polarization regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  COHERENT: '#16a34a',
  PARTIAL: '#65a30d',
  SPLIT: '#f59e0b',
  CROSS: '#ea580c',
  DEPOLARIZED: '#dc2626',
  SCRAMBLED: '#991b1b',
};

export const CognitivePolarizationPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reading' | 'rotation'>('overview');

  // Readings / filters / rotations
  const [readings, setReadings] = useState<any[]>([]);
  const [filters, setFilters] = useState<any[]>([]);
  const [rotations, setRotations] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    axis: 'GOAL',
    alignment_score: '',
    intensity: '',
    state: 'PARALLEL',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Apply filter form
  const [filterForm, setFilterForm] = useState({
    agent_id: '',
    axis: 'GOAL',
    filter_angle: '',
    transmitted_ratio: '',
  });

  // Rotate axis form
  const [rotationForm, setRotationForm] = useState({
    agent_id: '',
    from_axis: 'GOAL',
    to_axis: 'EVIDENCE',
    rotation_amount: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitivePolarization.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive polarization stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitivePolarization.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadFilters = async () => {
    try {
      const result = await api.cognitivePolarization.listFilters();
      const list = Array.isArray(result) ? result : (result?.filters ?? []);
      setFilters(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load filters');
    }
  };

  const loadRotations = async () => {
    try {
      const result = await api.cognitivePolarization.listRotations();
      const list = Array.isArray(result) ? result : (result?.rotations ?? []);
      setRotations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load rotations');
    }
  };

  // Initial load
  useEffect(() => {
    loadStats();
    loadReadings();
  }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadFilters();
      loadRotations();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      axis: readingForm.axis,
      alignment_score: readingForm.alignment_score.trim() === '' ? 0.5 : Number(readingForm.alignment_score),
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
      state: readingForm.state,
    };
    try {
      await api.cognitivePolarization.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', axis: 'GOAL', alignment_score: '', intensity: '', state: 'PARALLEL' });
      await loadReadings();
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
      const result = await api.cognitivePolarization.takeSnapshot(payload);
      setSnapshotResult(result);
      toast.success('Snapshot taken');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyFilter = async () => {
    if (!filterForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: filterForm.agent_id.trim(),
      axis: filterForm.axis,
      filter_angle: filterForm.filter_angle.trim() === '' ? 0 : Number(filterForm.filter_angle),
      transmitted_ratio: filterForm.transmitted_ratio.trim() === '' ? 0.5 : Number(filterForm.transmitted_ratio),
    };
    try {
      await api.cognitivePolarization.applyFilter(payload);
      toast.success('Filter applied');
      setFilterForm({ agent_id: '', axis: 'GOAL', filter_angle: '', transmitted_ratio: '' });
      await loadFilters();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRotateAxis = async () => {
    if (!rotationForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: rotationForm.agent_id.trim(),
      from_axis: rotationForm.from_axis,
      to_axis: rotationForm.to_axis,
      rotation_amount: rotationForm.rotation_amount.trim() === '' ? 0 : Number(rotationForm.rotation_amount),
    };
    try {
      await api.cognitivePolarization.rotateAxis(payload);
      toast.success('Axis rotated');
      setRotationForm({ agent_id: '', from_axis: 'GOAL', to_axis: 'EVIDENCE', rotation_amount: '' });
      await loadRotations();
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
          <h2>🧭 Cognitive Polarization Engine</h2>
          <p className="panel-subtitle">Record polarization readings, apply filters, and rotate axes across the cognitive alignment system</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive polarization...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧭 Cognitive Polarization Engine</h2>
        <p className="panel-subtitle">Record polarization readings, apply filters, and rotate axes across the cognitive alignment system</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Total Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_filters ?? '-'}</span><span className="stat-label">Filters</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_rotations ?? '-'}</span><span className="stat-label">Rotations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_alignment ?? '-'}</span><span className="stat-label">Avg Alignment</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reading', 'rotation'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Polarization Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Agents</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_agents ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Readings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_readings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Filters</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_filters ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Rotations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_rotations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Alignment</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_alignment ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dominant Regime</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Readings</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one in the Reading section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.axis ? ` · ${r.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.axis && renderBadge(r.axis, themeColors.secondary)}
                          {typeof r.alignment_score !== 'undefined' && renderBadge(`alignment ${r.alignment_score}`, themeColors.primary)}
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Filters</h3>
            <button onClick={() => loadFilters()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {filters.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No filters applied. Apply one in the Reading section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {filters.slice(0, 10).map((f: any, i: number) => {
                  const id = f.filter_id ?? f.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {f.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>filter {id}{f.axis ? ` · ${f.axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {f.axis && renderBadge(f.axis, themeColors.secondary)}
                          {typeof f.transmitted_ratio !== 'undefined' && renderBadge(`ratio ${f.transmitted_ratio}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Rotations</h3>
            <button onClick={() => loadRotations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {rotations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No rotations recorded. Rotate one in the Rotation section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {rotations.slice(0, 10).map((r: any, i: number) => {
                  const id = r.rotation_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>rotation {id}{r.from_axis ? ` · ${r.from_axis}→${r.to_axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.from_axis && renderBadge(r.from_axis, themeColors.secondary)}
                          {r.to_axis && renderBadge(r.to_axis, themeColors.secondary)}
                          {typeof r.rotation_amount !== 'undefined' && renderBadge(`amount ${r.rotation_amount}`, themeColors.primary)}
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

      {/* Reading Section */}
      {activeSection === 'reading' && (
        <div className="dashboard-section">
          {/* Record Reading */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reading</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={readingForm.axis} onChange={e => setReadingForm({ ...readingForm, axis: e.target.value })}>
                  {POLARIZATION_AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Alignment Score</label>
                <input className="form-input" value={readingForm.alignment_score} onChange={e => setReadingForm({ ...readingForm, alignment_score: e.target.value })} type="number" min="-1" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>Intensity</label>
                <input className="form-input" value={readingForm.intensity} onChange={e => setReadingForm({ ...readingForm, intensity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>State</label>
                <select className="form-select" value={readingForm.state} onChange={e => setReadingForm({ ...readingForm, state: e.target.value })}>
                  {ALIGNMENT_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRecordReading} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reading</button>
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

          {/* Apply Filter */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Apply Filter</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={filterForm.agent_id} onChange={e => setFilterForm({ ...filterForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Axis</label>
                <select className="form-select" value={filterForm.axis} onChange={e => setFilterForm({ ...filterForm, axis: e.target.value })}>
                  {POLARIZATION_AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Filter Angle</label>
                <input className="form-input" value={filterForm.filter_angle} onChange={e => setFilterForm({ ...filterForm, filter_angle: e.target.value })} type="number" min="0" max="360" step="0.01" placeholder="e.g. 45" />
              </div>
              <div className="form-group">
                <label>Transmitted Ratio</label>
                <input className="form-input" value={filterForm.transmitted_ratio} onChange={e => setFilterForm({ ...filterForm, transmitted_ratio: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
            </div>
            <button onClick={handleApplyFilter} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Filter</button>
          </div>
        </div>
      )}

      {/* Rotation Section */}
      {activeSection === 'rotation' && (
        <div className="dashboard-section">
          {/* Rotate Axis */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Rotate Axis</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={rotationForm.agent_id} onChange={e => setRotationForm({ ...rotationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>From Axis</label>
                <select className="form-select" value={rotationForm.from_axis} onChange={e => setRotationForm({ ...rotationForm, from_axis: e.target.value })}>
                  {POLARIZATION_AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>To Axis</label>
                <select className="form-select" value={rotationForm.to_axis} onChange={e => setRotationForm({ ...rotationForm, to_axis: e.target.value })}>
                  {POLARIZATION_AXES.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Rotation Amount</label>
                <input className="form-input" value={rotationForm.rotation_amount} onChange={e => setRotationForm({ ...rotationForm, rotation_amount: e.target.value })} type="number" min="0" max="360" step="0.01" placeholder="e.g. 90" />
              </div>
            </div>
            <button onClick={handleRotateAxis} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Rotate Axis</button>
          </div>

          {/* Rotations List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Rotations ({rotations.length})</h3>
            <button onClick={() => loadRotations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {rotations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No rotations recorded. Rotate one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {rotations.slice(0, 30).map((r: any, i: number) => {
                  const id = r.rotation_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>rotation {id}{r.from_axis ? ` · ${r.from_axis}→${r.to_axis}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.from_axis && renderBadge(r.from_axis, themeColors.secondary)}
                          {r.to_axis && renderBadge(r.to_axis, themeColors.secondary)}
                          {typeof r.rotation_amount !== 'undefined' && renderBadge(`amount ${r.rotation_amount}`, themeColors.primary)}
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

export default CognitivePolarizationPanel;
