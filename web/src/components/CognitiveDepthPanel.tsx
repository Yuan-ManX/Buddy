import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: emerald for cognitive depth
const themeColors = {
  primary: '#059669',
  secondary: '#10b981',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

// Enum values must match backend DepthDimension / DepthRegime / DeepeningMove / SurfacingMove / DepthTrajectory exactly (uppercase).
const DEPTH_DIMENSIONS = ['ABSTRACTION', 'RECURSION', 'FOUNDATIONAL', 'COUNTERFACTUAL', 'EXPLANATORY', 'TELEOLOGICAL'];
const DEPTH_REGIMES = ['SHALLOW', 'SURFACE', 'MODERATE', 'DEEP', 'PROFOUND', 'ABYSSAL'];
const DEEPENING_MOVES = ['ASK_WHY', 'ABSTRACT_UP', 'CONCRETIZE_DOWN', 'QUESTION_ASSUMPTION', 'CONSIDER_COUNTERFACTUAL', 'RECURSE', 'GROUND_IN_PRINCIPLE'];
const SURFACING_MOVES = ['SUMMARIZE', 'ANCHOR_EXAMPLE', 'STATE_CONCLUSION', 'CITE_RESULT', 'DEFER'];
const DEPTH_TRAJECTORIES = ['DESCENDING', 'HOLDING', 'ASCENDING', 'OSCILLATING', 'PLUNGING', 'BOTTOMING_OUT'];

// Map a depth regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  SHALLOW: '#9ca3af',
  SURFACE: '#0ea5e9',
  MODERATE: '#14b8a6',
  DEEP: '#059669',
  PROFOUND: '#7c3aed',
  ABYSSAL: '#dc2626',
};

export const CognitiveDepthPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'probe' | 'trajectory'>('overview');

  // Probes / assessments / trajectories
  const [probes, setProbes] = useState<any[]>([]);
  const [assessments, setAssessments] = useState<any[]>([]);
  const [trajectories, setTrajectories] = useState<any[]>([]);
  const [deepeningResult, setDeepeningResult] = useState<any>(null);
  const [surfacingResult, setSurfacingResult] = useState<any>(null);

  // Probe depth form
  const [probeForm, setProbeForm] = useState({
    agent_id: '',
    dimension: 'ABSTRACTION',
    query: '',
    target_depth: '',
  });

  // Apply deepening form
  const [deepeningForm, setDeepeningForm] = useState({
    agent_id: '',
    probe_id: '',
    move: 'ASK_WHY',
    rationale: '',
  });

  // Apply surfacing form
  const [surfacingForm, setSurfacingForm] = useState({
    agent_id: '',
    probe_id: '',
    move: 'SUMMARIZE',
    rationale: '',
  });

  // Record trajectory form
  const [trajectoryForm, setTrajectoryForm] = useState({
    agent_id: '',
    probe_id: '',
    trajectory: 'DESCENDING',
    velocity: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveDepth.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive depth stats');
    } finally {
      setLoading(false);
    }
  };

  const loadProbes = async () => {
    try {
      const result = await api.cognitiveDepth.listProbes();
      const list = Array.isArray(result) ? result : (result?.probes ?? []);
      setProbes(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load probes');
    }
  };

  const loadAssessments = async () => {
    try {
      const result = await api.cognitiveDepth.listAssessments();
      const list = Array.isArray(result) ? result : (result?.assessments ?? []);
      setAssessments(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load assessments');
    }
  };

  const loadTrajectories = async () => {
    try {
      const result = await api.cognitiveDepth.listTrajectories();
      const list = Array.isArray(result) ? result : (result?.trajectories ?? []);
      setTrajectories(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load trajectories');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadProbes();
      loadAssessments();
      loadTrajectories();
    }
  }, [activeSection]);

  const handleProbeDepth = async () => {
    if (!probeForm.agent_id.trim() || !probeForm.query.trim()) {
      toast.error('Agent ID and query are required');
      return;
    }
    const payload: any = {
      agent_id: probeForm.agent_id.trim(),
      dimension: probeForm.dimension,
      query: probeForm.query.trim(),
    };
    if (probeForm.target_depth.trim()) payload.target_depth = Number(probeForm.target_depth);
    try {
      await api.cognitiveDepth.probeDepth(payload);
      toast.success('Depth probed');
      setProbeForm({ agent_id: '', dimension: 'ABSTRACTION', query: '', target_depth: '' });
      await loadProbes();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyDeepening = async () => {
    if (!deepeningForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: deepeningForm.agent_id.trim(),
      move: deepeningForm.move,
    };
    if (deepeningForm.probe_id.trim()) payload.probe_id = deepeningForm.probe_id.trim();
    if (deepeningForm.rationale.trim()) payload.rationale = deepeningForm.rationale.trim();
    try {
      const result = await api.cognitiveDepth.applyDeepening(payload);
      setDeepeningResult(result);
      toast.success('Deepening applied');
      await loadAssessments();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplySurfacing = async () => {
    if (!surfacingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: surfacingForm.agent_id.trim(),
      move: surfacingForm.move,
    };
    if (surfacingForm.probe_id.trim()) payload.probe_id = surfacingForm.probe_id.trim();
    if (surfacingForm.rationale.trim()) payload.rationale = surfacingForm.rationale.trim();
    try {
      const result = await api.cognitiveDepth.applySurfacing(payload);
      setSurfacingResult(result);
      toast.success('Surfacing applied');
      await loadAssessments();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordTrajectory = async () => {
    if (!trajectoryForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: trajectoryForm.agent_id.trim(),
      trajectory: trajectoryForm.trajectory,
    };
    if (trajectoryForm.probe_id.trim()) payload.probe_id = trajectoryForm.probe_id.trim();
    if (trajectoryForm.velocity.trim()) payload.velocity = Number(trajectoryForm.velocity);
    try {
      await api.cognitiveDepth.recordTrajectory(payload);
      toast.success('Trajectory recorded');
      setTrajectoryForm({ agent_id: '', probe_id: '', trajectory: 'DESCENDING', velocity: '' });
      await loadTrajectories();
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
          <h2>🔍 Cognitive Depth</h2>
          <p className="panel-subtitle">Probe reasoning depth, apply deepening and surfacing moves, and track trajectories</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive depth...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔍 Cognitive Depth</h2>
        <p className="panel-subtitle">Probe reasoning depth, apply deepening and surfacing moves, and track trajectories</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_probes ?? '-'}</span><span className="stat-label">Probes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_assessments ?? '-'}</span><span className="stat-label">Assessments</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_deepenings ?? '-'}</span><span className="stat-label">Deepenings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_surfacings ?? '-'}</span><span className="stat-label">Surfacings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_trajectories ?? '-'}</span><span className="stat-label">Trajectories</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_depth ?? '-'}</span><span className="stat-label">Avg Depth</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'probe', 'trajectory'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Depth Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Probes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_probes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Assessments</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_assessments ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Deepenings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_deepenings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Surfacings</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_surfacings ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Trajectories</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_trajectories ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Depth</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_depth ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Probes</h3>
            <button onClick={() => loadProbes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {probes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No probes recorded. Record one in the Probe section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {probes.slice(0, 10).map((p: any, i: number) => {
                  const id = p.probe_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>probe {id}{p.query ? ` · ${p.query}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.dimension && renderBadge(p.dimension, themeColors.secondary)}
                          {p.regime && renderBadge(p.regime, statusColor(p.regime))}
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

      {/* Probe Section */}
      {activeSection === 'probe' && (
        <div className="dashboard-section">
          {/* Probe Depth */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Probe Depth</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={probeForm.agent_id} onChange={e => setProbeForm({ ...probeForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Dimension</label>
                <select value={probeForm.dimension} onChange={e => setProbeForm({ ...probeForm, dimension: e.target.value })}>
                  {DEPTH_DIMENSIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Depth</label>
                <input value={probeForm.target_depth} onChange={e => setProbeForm({ ...probeForm, target_depth: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Query *</label>
                <input value={probeForm.query} onChange={e => setProbeForm({ ...probeForm, query: e.target.value })} placeholder="e.g. why does this inference hold?" />
              </div>
            </div>
            <button onClick={handleProbeDepth} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Probe Depth</button>
          </div>

          {/* Apply Deepening */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Deepening</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={deepeningForm.agent_id} onChange={e => setDeepeningForm({ ...deepeningForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Probe ID</label>
                <input value={deepeningForm.probe_id} onChange={e => setDeepeningForm({ ...deepeningForm, probe_id: e.target.value })} placeholder="optional probe id" />
              </div>
              <div className="form-group">
                <label>Move</label>
                <select value={deepeningForm.move} onChange={e => setDeepeningForm({ ...deepeningForm, move: e.target.value })}>
                  {DEEPENING_MOVES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input value={deepeningForm.rationale} onChange={e => setDeepeningForm({ ...deepeningForm, rationale: e.target.value })} placeholder="optional rationale" />
              </div>
            </div>
            <button onClick={handleApplyDeepening} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Deepening</button>
            {deepeningResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(deepeningResult, null, 2)}</pre>
            )}
          </div>

          {/* Apply Surfacing */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Surfacing</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={surfacingForm.agent_id} onChange={e => setSurfacingForm({ ...surfacingForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Probe ID</label>
                <input value={surfacingForm.probe_id} onChange={e => setSurfacingForm({ ...surfacingForm, probe_id: e.target.value })} placeholder="optional probe id" />
              </div>
              <div className="form-group">
                <label>Move</label>
                <select value={surfacingForm.move} onChange={e => setSurfacingForm({ ...surfacingForm, move: e.target.value })}>
                  {SURFACING_MOVES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input value={surfacingForm.rationale} onChange={e => setSurfacingForm({ ...surfacingForm, rationale: e.target.value })} placeholder="optional rationale" />
              </div>
            </div>
            <button onClick={handleApplySurfacing} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Surfacing</button>
            {surfacingResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(surfacingResult, null, 2)}</pre>
            )}
          </div>

          {/* Probes List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Probes ({probes.length})</h3>
            <button onClick={() => loadProbes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {probes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No probes recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {probes.slice(0, 30).map((p: any, i: number) => {
                  const id = p.probe_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>probe {id}{p.query ? ` · ${p.query}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.dimension && renderBadge(p.dimension, themeColors.secondary)}
                          {p.regime && renderBadge(p.regime, statusColor(p.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Assessments List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Assessments ({assessments.length})</h3>
            <button onClick={() => loadAssessments()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {assessments.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No assessments recorded. Apply a deepening or surfacing move above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {assessments.slice(0, 30).map((a: any, i: number) => {
                  const id = a.assessment_id ?? a.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {a.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>assessment {id}{a.depth_score != null ? ` · depth: ${a.depth_score}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {a.dimension && renderBadge(a.dimension, themeColors.secondary)}
                          {a.regime && renderBadge(a.regime, statusColor(a.regime))}
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

      {/* Trajectory Section */}
      {activeSection === 'trajectory' && (
        <div className="dashboard-section">
          {/* Record Trajectory */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Trajectory</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={trajectoryForm.agent_id} onChange={e => setTrajectoryForm({ ...trajectoryForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Probe ID</label>
                <input value={trajectoryForm.probe_id} onChange={e => setTrajectoryForm({ ...trajectoryForm, probe_id: e.target.value })} placeholder="optional probe id" />
              </div>
              <div className="form-group">
                <label>Trajectory</label>
                <select value={trajectoryForm.trajectory} onChange={e => setTrajectoryForm({ ...trajectoryForm, trajectory: e.target.value })}>
                  {DEPTH_TRAJECTORIES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Velocity</label>
                <input value={trajectoryForm.velocity} onChange={e => setTrajectoryForm({ ...trajectoryForm, velocity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
            </div>
            <button onClick={handleRecordTrajectory} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Trajectory</button>
          </div>

          {/* Trajectories List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Trajectories ({trajectories.length})</h3>
            <button onClick={() => loadTrajectories()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {trajectories.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No trajectories recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {trajectories.slice(0, 30).map((t: any, i: number) => {
                  const id = t.trajectory_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {t.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>trajectory {id}{t.velocity != null ? ` · velocity: ${t.velocity}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {t.trajectory && renderBadge(t.trajectory, themeColors.secondary)}
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

export default CognitiveDepthPanel;
