import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: rose/red for cognitive refraction
const themeColors = {
  primary: '#e11d48',
  secondary: '#f43f5e',
  bg: '#fff1f2',
  border: '#fecdd3',
  accent: '#ffe4e6',
  text: '#881337',
};

// Enum values must match backend RefractionMedium / RefractionRegime / BendingDirection / SpectrumComponent / CorrectionStrategy exactly (uppercase).
const REFRACTION_MEDIUMS = ['ANALYTICAL', 'NARRATIVE', 'INTUITIVE', 'EMPIRICAL', 'DIALECTICAL', 'POETIC'];
const REFRACTION_REGIMES = ['TRANSPARENT', 'TRANSLUCENT', 'PRISMATIC', 'OPAQUE', 'TOTAL_REFLECTION'];
const BENDING_DIRECTIONS = ['CONVERGING', 'DIVERGING', 'PARALLEL', 'REVERSED', 'SCATTERED'];
const SPECTRUM_COMPONENTS = ['LITERAL', 'ANALOGICAL', 'METAPHORICAL', 'ABSTRACT', 'SYMBOLIC', 'PARADOXICAL'];
const CORRECTION_STRATEGIES = ['REFRAME', 'COMPENSATE', 'ANCHOR', 'DECOMPOSE', 'CALIBRATE', 'ACCEPT'];

// Map a refraction regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  TRANSPARENT: '#9ca3af',
  TRANSLUCENT: '#0ea5e9',
  PRISMATIC: '#e11d48',
  OPAQUE: '#f97316',
  TOTAL_REFLECTION: '#dc2626',
};

export const CognitiveRefractionPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'reading' | 'spectrum' | 'correction'>('overview');

  // Readings / spectrums / corrections
  const [readings, setReadings] = useState<any[]>([]);
  const [spectrums, setSpectrums] = useState<any[]>([]);
  const [corrections, setCorrections] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    medium: 'ANALYTICAL',
    input_angle: '',
    output_angle: '',
    refractive_index: '',
  });

  // Record bending form
  const [bendingForm, setBendingForm] = useState({
    agent_id: '',
    direction: 'CONVERGING',
    from_angle: '',
    to_angle: '',
    medium: 'ANALYTICAL',
  });

  // Capture spectrum form
  const [spectrumForm, setSpectrumForm] = useState({
    agent_id: '',
    medium: 'ANALYTICAL',
    components: '',
    spread: '',
    dominant_component: '',
  });

  // Plan correction form
  const [correctionForm, setCorrectionForm] = useState({
    agent_id: '',
    medium: 'ANALYTICAL',
    strategy: 'REFRAME',
    expected_correction: '',
    rationale: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveRefraction.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive refraction stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveRefraction.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadSpectrums = async () => {
    try {
      const result = await api.cognitiveRefraction.listSpectrums();
      const list = Array.isArray(result) ? result : (result?.spectrums ?? []);
      setSpectrums(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load spectrums');
    }
  };

  const loadCorrections = async () => {
    try {
      const result = await api.cognitiveRefraction.listCorrections();
      const list = Array.isArray(result) ? result : (result?.corrections ?? []);
      setCorrections(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load corrections');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadSpectrums();
      loadCorrections();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      medium: readingForm.medium,
      input_angle: Number(readingForm.input_angle),
      output_angle: Number(readingForm.output_angle),
      refractive_index: Number(readingForm.refractive_index),
    };
    try {
      await api.cognitiveRefraction.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', medium: 'ANALYTICAL', input_angle: '', output_angle: '', refractive_index: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordBending = async () => {
    if (!bendingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: bendingForm.agent_id.trim(),
      direction: bendingForm.direction,
      from_angle: Number(bendingForm.from_angle),
      to_angle: Number(bendingForm.to_angle),
      medium: bendingForm.medium,
    };
    try {
      await api.cognitiveRefraction.recordBending(payload);
      toast.success('Bending recorded');
      setBendingForm({ agent_id: '', direction: 'CONVERGING', from_angle: '', to_angle: '', medium: 'ANALYTICAL' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Enter an Agent ID in the reading form first');
      return;
    }
    try {
      const result = await api.cognitiveRefraction.takeSnapshot({ agent_id: readingForm.agent_id.trim() });
      setSnapshotResult(result);
      toast.success('Snapshot taken');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCaptureSpectrum = async () => {
    if (!spectrumForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const components = spectrumForm.components
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);
    if (components.length === 0) {
      toast.error('Provide at least one spectrum component');
      return;
    }
    const payload: any = {
      agent_id: spectrumForm.agent_id.trim(),
      medium: spectrumForm.medium,
      components,
      spread: Number(spectrumForm.spread),
    };
    if (spectrumForm.dominant_component.trim()) payload.dominant_component = spectrumForm.dominant_component.trim();
    try {
      await api.cognitiveRefraction.captureSpectrum(payload);
      toast.success('Spectrum captured');
      setSpectrumForm({ agent_id: '', medium: 'ANALYTICAL', components: '', spread: '', dominant_component: '' });
      await loadSpectrums();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanCorrection = async () => {
    if (!correctionForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: correctionForm.agent_id.trim(),
      medium: correctionForm.medium,
      strategy: correctionForm.strategy,
      expected_correction: Number(correctionForm.expected_correction),
    };
    if (correctionForm.rationale.trim()) payload.rationale = correctionForm.rationale.trim();
    try {
      await api.cognitiveRefraction.planCorrection(payload);
      toast.success('Correction planned');
      setCorrectionForm({ agent_id: '', medium: 'ANALYTICAL', strategy: 'REFRAME', expected_correction: '', rationale: '' });
      await loadCorrections();
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
          <h2>🔎 Cognitive Refraction</h2>
          <p className="panel-subtitle">Record refraction readings, capture spectrums, and plan corrections across cognitive mediums</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive refraction...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔎 Cognitive Refraction</h2>
        <p className="panel-subtitle">Record refraction readings, capture spectrums, and plan corrections across cognitive mediums</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_spectrums ?? '-'}</span><span className="stat-label">Spectrums</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_corrections ?? '-'}</span><span className="stat-label">Corrections</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_bends ?? '-'}</span><span className="stat-label">Bends</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_refractive_index ?? '-'}</span><span className="stat-label">Avg Refractive Index</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'reading', 'spectrum', 'correction'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Refraction Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Readings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_readings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Spectrums</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_spectrums ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Corrections</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_corrections ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Bends</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_bends ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Refractive Index</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_refractive_index ?? 0}</div>
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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.medium ? ` · ${r.medium}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.medium && renderBadge(r.medium, themeColors.secondary)}
                          {r.refractive_index != null && renderBadge(`n=${r.refractive_index}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Spectrums</h3>
            <button onClick={() => loadSpectrums()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {spectrums.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No spectrums captured. Capture one in the Spectrum section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {spectrums.slice(0, 10).map((s: any, i: number) => {
                  const id = s.capture_id ?? s.spectrum_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>spectrum {id}{s.medium ? ` · ${s.medium}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.medium && renderBadge(s.medium, themeColors.secondary)}
                          {s.spread != null && renderBadge(`spread=${s.spread}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Corrections</h3>
            <button onClick={() => loadCorrections()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {corrections.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No corrections planned. Plan one in the Correction section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {corrections.slice(0, 10).map((c: any, i: number) => {
                  const id = c.plan_id ?? c.correction_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>correction {id}{c.medium ? ` · ${c.medium}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.strategy && renderBadge(c.strategy, themeColors.secondary)}
                          {c.expected_correction != null && renderBadge(`Δ=${c.expected_correction}`, themeColors.primary)}
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
                <label>Medium</label>
                <select className="form-select" value={readingForm.medium} onChange={e => setReadingForm({ ...readingForm, medium: e.target.value })}>
                  {REFRACTION_MEDIUMS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Input Angle</label>
                <input className="form-input" value={readingForm.input_angle} onChange={e => setReadingForm({ ...readingForm, input_angle: e.target.value })} type="number" step="0.01" placeholder="e.g. 30.0" />
              </div>
              <div className="form-group">
                <label>Output Angle</label>
                <input className="form-input" value={readingForm.output_angle} onChange={e => setReadingForm({ ...readingForm, output_angle: e.target.value })} type="number" step="0.01" placeholder="e.g. 22.5" />
              </div>
              <div className="form-group">
                <label>Refractive Index</label>
                <input className="form-input" value={readingForm.refractive_index} onChange={e => setReadingForm({ ...readingForm, refractive_index: e.target.value })} type="number" step="0.01" placeholder="e.g. 1.33" />
              </div>
            </div>
            <div className="form-row" style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button onClick={handleRecordReading} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Record Reading</button>
              <button onClick={handleTakeSnapshot} className="btn-sm" style={{ background: themeColors.secondary, color: '#fff' }}>Take Snapshot</button>
            </div>
            {snapshotResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(snapshotResult, null, 2)}</pre>
            )}
          </div>

          {/* Record Bending */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Bending</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={bendingForm.agent_id} onChange={e => setBendingForm({ ...bendingForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Direction</label>
                <select className="form-select" value={bendingForm.direction} onChange={e => setBendingForm({ ...bendingForm, direction: e.target.value })}>
                  {BENDING_DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>From Angle</label>
                <input className="form-input" value={bendingForm.from_angle} onChange={e => setBendingForm({ ...bendingForm, from_angle: e.target.value })} type="number" step="0.01" placeholder="e.g. 30.0" />
              </div>
              <div className="form-group">
                <label>To Angle</label>
                <input className="form-input" value={bendingForm.to_angle} onChange={e => setBendingForm({ ...bendingForm, to_angle: e.target.value })} type="number" step="0.01" placeholder="e.g. 45.0" />
              </div>
              <div className="form-group">
                <label>Medium</label>
                <select className="form-select" value={bendingForm.medium} onChange={e => setBendingForm({ ...bendingForm, medium: e.target.value })}>
                  {REFRACTION_MEDIUMS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleRecordBending} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Bending</button>
          </div>

          {/* Readings List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Readings ({readings.length})</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 30).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.medium ? ` · ${r.medium}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.medium && renderBadge(r.medium, themeColors.secondary)}
                          {r.refractive_index != null && renderBadge(`n=${r.refractive_index}`, themeColors.primary)}
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

      {/* Spectrum Section */}
      {activeSection === 'spectrum' && (
        <div className="dashboard-section">
          {/* Capture Spectrum */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Capture Spectrum</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={spectrumForm.agent_id} onChange={e => setSpectrumForm({ ...spectrumForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Medium</label>
                <select className="form-select" value={spectrumForm.medium} onChange={e => setSpectrumForm({ ...spectrumForm, medium: e.target.value })}>
                  {REFRACTION_MEDIUMS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Spread</label>
                <input className="form-input" value={spectrumForm.spread} onChange={e => setSpectrumForm({ ...spectrumForm, spread: e.target.value })} type="number" step="0.01" placeholder="e.g. 12.5" />
              </div>
              <div className="form-group">
                <label>Dominant Component</label>
                <select className="form-select" value={spectrumForm.dominant_component} onChange={e => setSpectrumForm({ ...spectrumForm, dominant_component: e.target.value })}>
                  <option value="">— none —</option>
                  {SPECTRUM_COMPONENTS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Components (comma-separated) *</label>
                <input className="form-input" value={spectrumForm.components} onChange={e => setSpectrumForm({ ...spectrumForm, components: e.target.value })} placeholder="e.g. LITERAL,METAPHORICAL,ABSTRACT" />
              </div>
            </div>
            <button onClick={handleCaptureSpectrum} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Capture Spectrum</button>
          </div>

          {/* Spectrums List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Spectrums ({spectrums.length})</h3>
            <button onClick={() => loadSpectrums()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {spectrums.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No spectrums captured. Capture one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {spectrums.slice(0, 30).map((s: any, i: number) => {
                  const id = s.capture_id ?? s.spectrum_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>spectrum {id}{s.medium ? ` · ${s.medium}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.medium && renderBadge(s.medium, themeColors.secondary)}
                          {s.spread != null && renderBadge(`spread=${s.spread}`, themeColors.primary)}
                          {s.dominant_component && renderBadge(s.dominant_component, statusColor(s.dominant_component))}
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

      {/* Correction Section */}
      {activeSection === 'correction' && (
        <div className="dashboard-section">
          {/* Plan Correction */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Correction</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={correctionForm.agent_id} onChange={e => setCorrectionForm({ ...correctionForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Medium</label>
                <select className="form-select" value={correctionForm.medium} onChange={e => setCorrectionForm({ ...correctionForm, medium: e.target.value })}>
                  {REFRACTION_MEDIUMS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={correctionForm.strategy} onChange={e => setCorrectionForm({ ...correctionForm, strategy: e.target.value })}>
                  {CORRECTION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Correction</label>
                <input className="form-input" value={correctionForm.expected_correction} onChange={e => setCorrectionForm({ ...correctionForm, expected_correction: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.25" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={correctionForm.rationale} onChange={e => setCorrectionForm({ ...correctionForm, rationale: e.target.value })} placeholder="optional rationale" />
              </div>
            </div>
            <button onClick={handlePlanCorrection} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Correction</button>
          </div>

          {/* Corrections List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Corrections ({corrections.length})</h3>
            <button onClick={() => loadCorrections()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {corrections.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No corrections planned. Plan one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {corrections.slice(0, 30).map((c: any, i: number) => {
                  const id = c.plan_id ?? c.correction_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>correction {id}{c.medium ? ` · ${c.medium}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {c.strategy && renderBadge(c.strategy, themeColors.secondary)}
                          {c.expected_correction != null && renderBadge(`Δ=${c.expected_correction}`, themeColors.primary)}
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

export default CognitiveRefractionPanel;
