import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: rose for cognitive momentum
const themeColors = {
  primary: '#e11d48',
  secondary: '#f43f5e',
  bg: '#fff1f2',
  border: '#fecdd3',
  accent: '#ffe4e6',
  text: '#881337',
};

// Enum values must match backend MomentumRegime / PerturbationType / EscapeStrategy / ProgressSignal exactly (uppercase).
const MOMENTUM_REGIMES = ['INERT', 'DRIFTING', 'FOCUSED', 'HEAVY', 'LOCKED', 'BURSTING'];
const PERTURBATION_TYPES = ['CONTRARIAN', 'REFRAME', 'ANALOGY', 'RANDOM_INJECTION', 'DECOMPOSITION', 'ABSTRACTION', 'CONTEXT_SHIFT'];
const ESCAPE_STRATEGIES = ['WAIT', 'NUDGE', 'PIVOT', 'RESET', 'EXTERNAL_INPUT', 'DECOMPOSE', 'ABSTRACT'];
const PROGRESS_SIGNALS = ['FORWARD', 'LATERAL', 'BACKWARD', 'NONE'];

// Map a momentum regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  INERT: '#9ca3af',
  DRIFTING: '#0ea5e9',
  FOCUSED: '#16a34a',
  HEAVY: '#f59e0b',
  LOCKED: '#dc2626',
  BURSTING: '#e11d48',
};

export const CognitiveMomentumPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'vector' | 'escape'>('overview');

  // Vectors / stucks / perturbations
  const [vectors, setVectors] = useState<any[]>([]);
  const [stucks, setStucks] = useState<any[]>([]);
  const [perturbations, setPerturbations] = useState<any[]>([]);
  const [escapeVelocityResult, setEscapeVelocityResult] = useState<any>(null);
  const [escapePlanResult, setEscapePlanResult] = useState<any>(null);

  // Record vector form
  const [vectorForm, setVectorForm] = useState({
    agent_id: '',
    direction: '',
    magnitude: '',
    velocity: '',
    acceleration: '',
    curvature: '',
    mass: '',
  });

  // Record point form
  const [pointForm, setPointForm] = useState({
    agent_id: '',
    step: '',
    position: '',
    progress: 'FORWARD',
    reward: '',
  });

  // Detect stuck form
  const [stuckForm, setStuckForm] = useState({
    agent_id: '',
    trajectory_id: '',
    momentum_magnitude: '',
    progress_rate: '',
    curvature: '',
  });

  // Apply perturbation form
  const [perturbationForm, setPerturbationForm] = useState({
    agent_id: '',
    perturbation_type: 'CONTRARIAN',
    target_trajectory: '',
    intensity: '',
    expected_impact: '',
  });

  // Compute escape velocity form
  const [escapeVelocityForm, setEscapeVelocityForm] = useState({
    current_momentum: '',
    well_depth: '',
  });

  // Create escape plan form
  const [escapePlanForm, setEscapePlanForm] = useState({
    agent_id: '',
    trajectory_id: '',
    current_momentum: '',
    escape_velocity: '',
    strategy: 'NUDGE',
    estimated_steps: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveMomentum.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive momentum stats');
    } finally {
      setLoading(false);
    }
  };

  const loadVectors = async () => {
    try {
      const result = await api.cognitiveMomentum.listVectors();
      const list = Array.isArray(result) ? result : (result?.vectors ?? []);
      setVectors(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load vectors');
    }
  };

  const loadStucks = async () => {
    try {
      const result = await api.cognitiveMomentum.listStucks();
      const list = Array.isArray(result) ? result : (result?.stucks ?? []);
      setStucks(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load stuck detections');
    }
  };

  const loadPerturbations = async () => {
    try {
      const result = await api.cognitiveMomentum.listPerturbations();
      const list = Array.isArray(result) ? result : (result?.perturbations ?? []);
      setPerturbations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load perturbations');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadVectors();
      loadStucks();
      loadPerturbations();
    }
  }, [activeSection]);

  const handleRecordVector = async () => {
    if (!vectorForm.agent_id.trim() || !vectorForm.direction.trim() || !vectorForm.magnitude.trim()) {
      toast.error('Agent ID, direction, and magnitude are required');
      return;
    }
    const payload: any = {
      agent_id: vectorForm.agent_id.trim(),
      direction: vectorForm.direction.trim(),
      magnitude: Number(vectorForm.magnitude),
    };
    if (vectorForm.velocity.trim()) payload.velocity = Number(vectorForm.velocity);
    if (vectorForm.acceleration.trim()) payload.acceleration = Number(vectorForm.acceleration);
    if (vectorForm.curvature.trim()) payload.curvature = Number(vectorForm.curvature);
    if (vectorForm.mass.trim()) payload.mass = Number(vectorForm.mass);
    try {
      await api.cognitiveMomentum.recordVector(payload);
      toast.success('Vector recorded');
      setVectorForm({ agent_id: '', direction: '', magnitude: '', velocity: '', acceleration: '', curvature: '', mass: '' });
      await loadVectors();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordPoint = async () => {
    if (!pointForm.agent_id.trim() || !pointForm.step.trim() || !pointForm.position.trim()) {
      toast.error('Agent ID, step, and position are required');
      return;
    }
    let position: Record<string, number>;
    try { position = JSON.parse(pointForm.position); }
    catch { toast.error('Position must be valid JSON'); return; }
    const payload: any = {
      agent_id: pointForm.agent_id.trim(),
      step: Number(pointForm.step),
      position,
      progress: pointForm.progress,
    };
    if (pointForm.reward.trim()) payload.reward = Number(pointForm.reward);
    try {
      await api.cognitiveMomentum.recordPoint(payload);
      toast.success('Point recorded');
      setPointForm({ agent_id: '', step: '', position: '', progress: 'FORWARD', reward: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDetectStuck = async () => {
    if (!stuckForm.agent_id.trim() || !stuckForm.trajectory_id.trim() || !stuckForm.momentum_magnitude.trim() || !stuckForm.progress_rate.trim() || !stuckForm.curvature.trim()) {
      toast.error('All stuck detection fields are required');
      return;
    }
    const payload: any = {
      agent_id: stuckForm.agent_id.trim(),
      trajectory_id: stuckForm.trajectory_id.trim(),
      momentum_magnitude: Number(stuckForm.momentum_magnitude),
      progress_rate: Number(stuckForm.progress_rate),
      curvature: Number(stuckForm.curvature),
    };
    try {
      await api.cognitiveMomentum.detectStuck(payload);
      toast.success('Stuck detection recorded');
      setStuckForm({ agent_id: '', trajectory_id: '', momentum_magnitude: '', progress_rate: '', curvature: '' });
      await loadStucks();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleApplyPerturbation = async () => {
    if (!perturbationForm.agent_id.trim() || !perturbationForm.target_trajectory.trim()) {
      toast.error('Agent ID and target trajectory are required');
      return;
    }
    const payload: any = {
      agent_id: perturbationForm.agent_id.trim(),
      perturbation_type: perturbationForm.perturbation_type,
      target_trajectory: perturbationForm.target_trajectory.trim(),
    };
    if (perturbationForm.intensity.trim()) payload.intensity = Number(perturbationForm.intensity);
    if (perturbationForm.expected_impact.trim()) payload.expected_impact = Number(perturbationForm.expected_impact);
    try {
      await api.cognitiveMomentum.applyPerturbation(payload);
      toast.success('Perturbation applied');
      setPerturbationForm({ agent_id: '', perturbation_type: 'CONTRARIAN', target_trajectory: '', intensity: '', expected_impact: '' });
      await loadPerturbations();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleComputeEscapeVelocity = async () => {
    if (!escapeVelocityForm.current_momentum.trim() || !escapeVelocityForm.well_depth.trim()) {
      toast.error('Current momentum and well depth are required');
      return;
    }
    const payload: any = {
      current_momentum: Number(escapeVelocityForm.current_momentum),
      well_depth: Number(escapeVelocityForm.well_depth),
    };
    try {
      const result = await api.cognitiveMomentum.computeEscapeVelocity(payload);
      setEscapeVelocityResult(result);
      toast.success('Escape velocity computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateEscapePlan = async () => {
    if (!escapePlanForm.agent_id.trim() || !escapePlanForm.trajectory_id.trim() || !escapePlanForm.current_momentum.trim() || !escapePlanForm.escape_velocity.trim()) {
      toast.error('Agent ID, trajectory ID, current momentum, and escape velocity are required');
      return;
    }
    const payload: any = {
      agent_id: escapePlanForm.agent_id.trim(),
      trajectory_id: escapePlanForm.trajectory_id.trim(),
      current_momentum: Number(escapePlanForm.current_momentum),
      escape_velocity: Number(escapePlanForm.escape_velocity),
      strategy: escapePlanForm.strategy,
    };
    if (escapePlanForm.estimated_steps.trim()) payload.estimated_steps = Number(escapePlanForm.estimated_steps);
    try {
      const result = await api.cognitiveMomentum.createEscapePlan(payload);
      setEscapePlanResult(result);
      toast.success('Escape plan created');
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
          <h2>🚀 Cognitive Momentum</h2>
          <p className="panel-subtitle">Track vectors, detect stuck states, and plan escape from cognitive wells</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive momentum...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🚀 Cognitive Momentum</h2>
        <p className="panel-subtitle">Track vectors, detect stuck states, and plan escape from cognitive wells</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_vectors ?? '-'}</span><span className="stat-label">Vectors</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_points ?? '-'}</span><span className="stat-label">Points</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_stuck_detections ?? '-'}</span><span className="stat-label">Stucks</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_perturbations ?? '-'}</span><span className="stat-label">Perturbations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_escapes ?? '-'}</span><span className="stat-label">Escapes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_momentum ?? '-'}</span><span className="stat-label">Avg Momentum</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_escape_velocity ?? '-'}</span><span className="stat-label">Avg Escape</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'vector', 'escape'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Momentum Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Vectors</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_vectors ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Points</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_points ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Stuck Detections</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_stuck_detections ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Perturbations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_perturbations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Escapes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_escapes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Momentum</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_momentum ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Escape Velocity</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_escape_velocity ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Vectors</h3>
            <button onClick={() => loadVectors()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {vectors.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No vectors recorded. Record one in the Vector section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {vectors.slice(0, 10).map((v: any, i: number) => {
                  const id = v.vector_id ?? v.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {v.agent_id ?? '-'} · {v.direction ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>vector {id} · magnitude: {v.magnitude ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {v.regime && renderBadge(v.regime, statusColor(v.regime))}
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

      {/* Vector Section */}
      {activeSection === 'vector' && (
        <div className="dashboard-section">
          {/* Record Vector */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Vector</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={vectorForm.agent_id} onChange={e => setVectorForm({ ...vectorForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Direction *</label>
                <input value={vectorForm.direction} onChange={e => setVectorForm({ ...vectorForm, direction: e.target.value })} placeholder="e.g. forward_reasoning" />
              </div>
              <div className="form-group">
                <label>Magnitude *</label>
                <input value={vectorForm.magnitude} onChange={e => setVectorForm({ ...vectorForm, magnitude: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.8" />
              </div>
              <div className="form-group">
                <label>Velocity</label>
                <input value={vectorForm.velocity} onChange={e => setVectorForm({ ...vectorForm, velocity: e.target.value })} type="number" step="0.01" placeholder="e.g. 1.2" />
              </div>
              <div className="form-group">
                <label>Acceleration</label>
                <input value={vectorForm.acceleration} onChange={e => setVectorForm({ ...vectorForm, acceleration: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.05" />
              </div>
              <div className="form-group">
                <label>Curvature</label>
                <input value={vectorForm.curvature} onChange={e => setVectorForm({ ...vectorForm, curvature: e.target.value })} type="number" step="0.001" placeholder="e.g. 0.02" />
              </div>
              <div className="form-group">
                <label>Mass</label>
                <input value={vectorForm.mass} onChange={e => setVectorForm({ ...vectorForm, mass: e.target.value })} type="number" step="0.01" placeholder="e.g. 2.5" />
              </div>
            </div>
            <button onClick={handleRecordVector} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Vector</button>
          </div>

          {/* Record Point */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Point</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={pointForm.agent_id} onChange={e => setPointForm({ ...pointForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Step *</label>
                <input value={pointForm.step} onChange={e => setPointForm({ ...pointForm, step: e.target.value })} type="number" min="0" placeholder="e.g. 7" />
              </div>
              <div className="form-group">
                <label>Progress</label>
                <select value={pointForm.progress} onChange={e => setPointForm({ ...pointForm, progress: e.target.value })}>
                  {PROGRESS_SIGNALS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Reward</label>
                <input value={pointForm.reward} onChange={e => setPointForm({ ...pointForm, reward: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Position (JSON) *</label>
                <textarea value={pointForm.position} onChange={e => setPointForm({ ...pointForm, position: e.target.value })} placeholder='{"x":0.5,"y":0.3}' rows={3} style={{ width: '100%', fontFamily: 'monospace' }} />
              </div>
            </div>
            <button onClick={handleRecordPoint} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Point</button>
          </div>

          {/* Vectors List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Vectors ({vectors.length})</h3>
            <button onClick={() => loadVectors()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {vectors.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No vectors recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {vectors.slice(0, 30).map((v: any, i: number) => {
                  const id = v.vector_id ?? v.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {v.agent_id ?? '-'} · {v.direction ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>vector {id} · magnitude: {v.magnitude ?? '-'} · velocity: {v.velocity ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {v.regime && renderBadge(v.regime, statusColor(v.regime))}
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

      {/* Escape Section */}
      {activeSection === 'escape' && (
        <div className="dashboard-section">
          {/* Detect Stuck */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Detect Stuck</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={stuckForm.agent_id} onChange={e => setStuckForm({ ...stuckForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Trajectory ID *</label>
                <input value={stuckForm.trajectory_id} onChange={e => setStuckForm({ ...stuckForm, trajectory_id: e.target.value })} placeholder="trajectory id" />
              </div>
              <div className="form-group">
                <label>Momentum Magnitude *</label>
                <input value={stuckForm.momentum_magnitude} onChange={e => setStuckForm({ ...stuckForm, momentum_magnitude: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.1" />
              </div>
              <div className="form-group">
                <label>Progress Rate *</label>
                <input value={stuckForm.progress_rate} onChange={e => setStuckForm({ ...stuckForm, progress_rate: e.target.value })} type="number" step="0.001" placeholder="e.g. 0.02" />
              </div>
              <div className="form-group">
                <label>Curvature *</label>
                <input value={stuckForm.curvature} onChange={e => setStuckForm({ ...stuckForm, curvature: e.target.value })} type="number" step="0.001" placeholder="e.g. 0.85" />
              </div>
            </div>
            <button onClick={handleDetectStuck} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Detect Stuck</button>
          </div>

          {/* Apply Perturbation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Apply Perturbation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={perturbationForm.agent_id} onChange={e => setPerturbationForm({ ...perturbationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Perturbation Type</label>
                <select value={perturbationForm.perturbation_type} onChange={e => setPerturbationForm({ ...perturbationForm, perturbation_type: e.target.value })}>
                  {PERTURBATION_TYPES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Trajectory *</label>
                <input value={perturbationForm.target_trajectory} onChange={e => setPerturbationForm({ ...perturbationForm, target_trajectory: e.target.value })} placeholder="trajectory id" />
              </div>
              <div className="form-group">
                <label>Intensity</label>
                <input value={perturbationForm.intensity} onChange={e => setPerturbationForm({ ...perturbationForm, intensity: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group">
                <label>Expected Impact</label>
                <input value={perturbationForm.expected_impact} onChange={e => setPerturbationForm({ ...perturbationForm, expected_impact: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.3" />
              </div>
            </div>
            <button onClick={handleApplyPerturbation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Apply Perturbation</button>
          </div>

          {/* Compute Escape Velocity */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Compute Escape Velocity</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Current Momentum *</label>
                <input value={escapeVelocityForm.current_momentum} onChange={e => setEscapeVelocityForm({ ...escapeVelocityForm, current_momentum: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>Well Depth *</label>
                <input value={escapeVelocityForm.well_depth} onChange={e => setEscapeVelocityForm({ ...escapeVelocityForm, well_depth: e.target.value })} type="number" step="0.01" placeholder="e.g. 1.2" />
              </div>
            </div>
            <button onClick={handleComputeEscapeVelocity} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Compute</button>
            {escapeVelocityResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(escapeVelocityResult, null, 2)}</pre>
            )}
          </div>

          {/* Create Escape Plan */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Escape Plan</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={escapePlanForm.agent_id} onChange={e => setEscapePlanForm({ ...escapePlanForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Trajectory ID *</label>
                <input value={escapePlanForm.trajectory_id} onChange={e => setEscapePlanForm({ ...escapePlanForm, trajectory_id: e.target.value })} placeholder="trajectory id" />
              </div>
              <div className="form-group">
                <label>Current Momentum *</label>
                <input value={escapePlanForm.current_momentum} onChange={e => setEscapePlanForm({ ...escapePlanForm, current_momentum: e.target.value })} type="number" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>Escape Velocity *</label>
                <input value={escapePlanForm.escape_velocity} onChange={e => setEscapePlanForm({ ...escapePlanForm, escape_velocity: e.target.value })} type="number" step="0.01" placeholder="e.g. 1.5" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={escapePlanForm.strategy} onChange={e => setEscapePlanForm({ ...escapePlanForm, strategy: e.target.value })}>
                  {ESCAPE_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Estimated Steps</label>
                <input value={escapePlanForm.estimated_steps} onChange={e => setEscapePlanForm({ ...escapePlanForm, estimated_steps: e.target.value })} type="number" min="0" placeholder="e.g. 5" />
              </div>
            </div>
            <button onClick={handleCreateEscapePlan} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Escape Plan</button>
            {escapePlanResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(escapePlanResult, null, 2)}</pre>
            )}
          </div>

          {/* Stucks List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Stuck Detections ({stucks.length})</h3>
            <button onClick={() => loadStucks()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {stucks.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No stuck detections. Detect one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {stucks.slice(0, 30).map((s: any, i: number) => {
                  const id = s.detection_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'} · trajectory: {s.trajectory_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>stuck {id} · momentum: {s.momentum_magnitude ?? '-'}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {s.regime && renderBadge(s.regime, statusColor(s.regime))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Perturbations List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Perturbations ({perturbations.length})</h3>
            <button onClick={() => loadPerturbations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {perturbations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No perturbations recorded. Apply one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {perturbations.slice(0, 30).map((p: any, i: number) => {
                  const id = p.event_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'} · target: {p.target_trajectory ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>perturbation {id}{p.intensity != null ? ` · intensity: ${p.intensity}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.perturbation_type && renderBadge(p.perturbation_type, themeColors.secondary)}
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

export default CognitiveMomentumPanel;
