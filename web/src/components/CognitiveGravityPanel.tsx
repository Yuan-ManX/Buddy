import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: slate for cognitive gravity
const themeColors = {
  primary: '#475569',
  secondary: '#64748b',
  bg: '#f8fafc',
  border: '#cbd5e1',
  accent: '#e2e8f0',
  text: '#1e293b',
};

// Enum values must match backend AttractorType / MassContribution / TrajectoryStatus / FieldState exactly (uppercase).
const ATTRACTOR_TYPES = ['POINT', 'BASIN', 'RIDGE', 'SADDLE', 'STRANGE'];
const MASS_CONTRIBUTIONS = ['EVIDENCE', 'SALIENCE', 'CONNECTIVITY', 'COHERENCE', 'EMOTIONAL'];
const TRAJECTORY_STATUS = ['ACTIVE', 'SETTLED', 'ESCAPED', 'ORBITING'];
const FIELD_STATES = ['STABLE', 'PERTURBED', 'COLLAPSING', 'EXPANDING'];

// Map a status value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  ACTIVE: '#0ea5e9',
  SETTLED: '#16a34a',
  ESCAPED: '#dc2626',
  ORBITING: '#f59e0b',
};

export const CognitiveGravityPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'context' | 'trajectory'>('overview');

  // Contexts / trajectories / basins
  const [contexts, setContexts] = useState<any[]>([]);
  const [trajectories, setTrajectories] = useState<any[]>([]);
  const [fieldResult, setFieldResult] = useState<any>(null);
  const [escapeResult, setEscapeResult] = useState<any>(null);
  const [predictResult, setPredictResult] = useState<any>(null);

  // Register context form
  const [contextForm, setContextForm] = useState({
    agent_id: '',
    description: '',
  });

  // Add concept form
  const [conceptForm, setConceptForm] = useState({
    context_id: '',
    concept: '',
    mass: '1.0',
    position: '',
    contributions: '',
  });

  // Create basin form
  const [basinForm, setBasinForm] = useState({
    context_id: '',
    center_concept: '',
    attractor_type: 'BASIN',
    radius: '1.0',
    stability: '0.5',
  });

  // Compute field form
  const [fieldForm, setFieldForm] = useState({ context_id: '' });

  // Predict trajectory form
  const [predictForm, setPredictForm] = useState({
    context_id: '',
    start_concept: '',
    steps: '10',
    step_size: '0.5',
  });

  // Check escape form
  const [escapeForm, setEscapeForm] = useState({ trajectory_id: '' });

  // Perturb field form
  const [perturbForm, setPerturbForm] = useState({
    context_id: '',
    concept: '',
    force_vector: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveGravity.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive gravity stats');
    } finally {
      setLoading(false);
    }
  };

  const loadContexts = async () => {
    try {
      const result = await api.cognitiveGravity.listContexts();
      const list = Array.isArray(result) ? result : (result?.contexts ?? []);
      setContexts(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load contexts');
    }
  };

  const loadTrajectories = async () => {
    try {
      const result = await api.cognitiveGravity.listTrajectories();
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
      loadContexts();
      loadTrajectories();
    }
  }, [activeSection]);

  const handleRegisterContext = async () => {
    if (!contextForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = { agent_id: contextForm.agent_id.trim() };
    if (contextForm.description.trim()) payload.description = contextForm.description.trim();
    try {
      await api.cognitiveGravity.registerContext(payload);
      toast.success('Context registered');
      setContextForm({ agent_id: '', description: '' });
      await loadContexts();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddConcept = async () => {
    if (!conceptForm.context_id.trim() || !conceptForm.concept.trim()) {
      toast.error('Context ID and concept are required');
      return;
    }
    const payload: any = { concept: conceptForm.concept.trim() };
    if (conceptForm.mass.trim()) {
      const mass = Number(conceptForm.mass);
      if (!Number.isNaN(mass)) payload.mass = mass;
    }
    if (conceptForm.position.trim()) {
      try { payload.position = JSON.parse(conceptForm.position); }
      catch { toast.error('Position must be valid JSON'); return; }
    }
    if (conceptForm.contributions.trim()) {
      try { payload.contributions = JSON.parse(conceptForm.contributions); }
      catch { toast.error('Contributions must be valid JSON'); return; }
    }
    try {
      await api.cognitiveGravity.addConcept(conceptForm.context_id.trim(), payload);
      toast.success('Concept added');
      setConceptForm({ context_id: '', concept: '', mass: '1.0', position: '', contributions: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateBasin = async () => {
    if (!basinForm.context_id.trim() || !basinForm.center_concept.trim()) {
      toast.error('Context ID and center concept are required');
      return;
    }
    const payload: any = {
      center_concept: basinForm.center_concept.trim(),
      attractor_type: basinForm.attractor_type,
    };
    if (basinForm.radius.trim()) {
      const radius = Number(basinForm.radius);
      if (!Number.isNaN(radius)) payload.radius = radius;
    }
    if (basinForm.stability.trim()) {
      const stability = Number(basinForm.stability);
      if (!Number.isNaN(stability)) payload.stability = stability;
    }
    try {
      await api.cognitiveGravity.createBasin(basinForm.context_id.trim(), payload);
      toast.success('Basin created');
      setBasinForm({ context_id: '', center_concept: '', attractor_type: 'BASIN', radius: '1.0', stability: '0.5' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleComputeField = async () => {
    if (!fieldForm.context_id.trim()) {
      toast.error('Context ID is required');
      return;
    }
    try {
      const result = await api.cognitiveGravity.computeField(fieldForm.context_id.trim());
      setFieldResult(result);
      toast.success('Field computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePredictTrajectory = async () => {
    if (!predictForm.context_id.trim() || !predictForm.start_concept.trim()) {
      toast.error('Context ID and start concept are required');
      return;
    }
    const payload: any = { start_concept: predictForm.start_concept.trim() };
    if (predictForm.steps.trim()) {
      const steps = Number(predictForm.steps);
      if (!Number.isNaN(steps)) payload.steps = steps;
    }
    if (predictForm.step_size.trim()) {
      const stepSize = Number(predictForm.step_size);
      if (!Number.isNaN(stepSize)) payload.step_size = stepSize;
    }
    try {
      const result = await api.cognitiveGravity.predictTrajectory(predictForm.context_id.trim(), payload);
      setPredictResult(result);
      toast.success('Trajectory predicted');
      await loadTrajectories();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCheckEscape = async () => {
    if (!escapeForm.trajectory_id.trim()) {
      toast.error('Trajectory ID is required');
      return;
    }
    try {
      const result = await api.cognitiveGravity.checkBasinEscape(escapeForm.trajectory_id.trim());
      setEscapeResult(result);
      toast.success('Escape checked');
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePerturb = async () => {
    if (!perturbForm.context_id.trim() || !perturbForm.concept.trim() || !perturbForm.force_vector.trim()) {
      toast.error('Context ID, concept, and force vector are required');
      return;
    }
    let forceVector: number[];
    try { forceVector = JSON.parse(perturbForm.force_vector); }
    catch { toast.error('Force vector must be valid JSON'); return; }
    if (!Array.isArray(forceVector)) {
      toast.error('Force vector must be a JSON array');
      return;
    }
    const payload: any = { concept: perturbForm.concept.trim(), force_vector: forceVector };
    try {
      await api.cognitiveGravity.perturbField(perturbForm.context_id.trim(), payload);
      toast.success('Field perturbed');
      setPerturbForm({ context_id: '', concept: '', force_vector: '' });
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
          <h2>🪐 Cognitive Gravity</h2>
          <p className="panel-subtitle">Model concept masses, attractor basins, and trajectory dynamics</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive gravity...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🪐 Cognitive Gravity</h2>
        <p className="panel-subtitle">Model concept masses, attractor basins, and trajectory dynamics</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_contexts ?? '-'}</span><span className="stat-label">Contexts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_concepts ?? '-'}</span><span className="stat-label">Concepts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_basins ?? '-'}</span><span className="stat-label">Basins</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_trajectories ?? '-'}</span><span className="stat-label">Trajectories</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_trajectories ?? '-'}</span><span className="stat-label">Active</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'context', 'trajectory'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Gravity Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Contexts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_contexts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Concepts</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_concepts ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Basins</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_basins ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Trajectories</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_trajectories ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Trajectories</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_trajectories ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Contexts</h3>
            <button onClick={() => loadContexts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {contexts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No contexts recorded. Register one in the Context section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {contexts.slice(0, 10).map((c: any, i: number) => {
                  const id = c.context_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{c.description ?? ''} · {id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Context Section */}
      {activeSection === 'context' && (
        <div className="dashboard-section">
          {/* Register Context */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Context</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={contextForm.agent_id} onChange={e => setContextForm({ ...contextForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={contextForm.description} onChange={e => setContextForm({ ...contextForm, description: e.target.value })} placeholder="Optional description" />
              </div>
            </div>
            <button onClick={handleRegisterContext} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Context</button>
          </div>

          {/* Add Concept */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Concept</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={conceptForm.context_id} onChange={e => setConceptForm({ ...conceptForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Concept *</label>
                <input value={conceptForm.concept} onChange={e => setConceptForm({ ...conceptForm, concept: e.target.value })} placeholder="e.g. core_hypothesis" />
              </div>
              <div className="form-group">
                <label>Mass</label>
                <input value={conceptForm.mass} onChange={e => setConceptForm({ ...conceptForm, mass: e.target.value })} type="number" min="0" step="0.1" />
              </div>
              <div className="form-group">
                <label>Position (JSON)</label>
                <input value={conceptForm.position} onChange={e => setConceptForm({ ...conceptForm, position: e.target.value })} placeholder="[0.1, 0.2, 0.3]" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Contributions (JSON)</label>
                <input value={conceptForm.contributions} onChange={e => setConceptForm({ ...conceptForm, contributions: e.target.value })} placeholder='{"EVIDENCE": 0.4, "SALIENCE": 0.6}' />
              </div>
            </div>
            <button onClick={handleAddConcept} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Concept</button>
          </div>

          {/* Create Basin */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Basin</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={basinForm.context_id} onChange={e => setBasinForm({ ...basinForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Center Concept *</label>
                <input value={basinForm.center_concept} onChange={e => setBasinForm({ ...basinForm, center_concept: e.target.value })} placeholder="center concept name" />
              </div>
              <div className="form-group">
                <label>Attractor Type</label>
                <select value={basinForm.attractor_type} onChange={e => setBasinForm({ ...basinForm, attractor_type: e.target.value })}>
                  {ATTRACTOR_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Radius</label>
                <input value={basinForm.radius} onChange={e => setBasinForm({ ...basinForm, radius: e.target.value })} type="number" min="0" step="0.1" />
              </div>
              <div className="form-group">
                <label>Stability</label>
                <input value={basinForm.stability} onChange={e => setBasinForm({ ...basinForm, stability: e.target.value })} type="number" min="0" max="1" step="0.1" />
              </div>
            </div>
            <button onClick={handleCreateBasin} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Basin</button>
          </div>

          {/* Perturb Field */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Perturb Field</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={perturbForm.context_id} onChange={e => setPerturbForm({ ...perturbForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Concept *</label>
                <input value={perturbForm.concept} onChange={e => setPerturbForm({ ...perturbForm, concept: e.target.value })} placeholder="concept to perturb" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Force Vector (JSON) *</label>
                <input value={perturbForm.force_vector} onChange={e => setPerturbForm({ ...perturbForm, force_vector: e.target.value })} placeholder="[0.5, -0.3, 0.2]" />
              </div>
            </div>
            <button onClick={handlePerturb} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Perturb</button>
          </div>

          {/* Contexts List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Contexts ({contexts.length})</h3>
            <button onClick={() => loadContexts()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {contexts.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No contexts recorded. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {contexts.slice(0, 30).map((c: any, i: number) => {
                  const id = c.context_id ?? c.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {c.agent_id ?? '-'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                      {c.description && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{c.description}</div>
                      )}
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
          {/* Compute Field */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Compute Field</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={fieldForm.context_id} onChange={e => setFieldForm({ ...fieldForm, context_id: e.target.value })} placeholder="context id" />
              </div>
            </div>
            <button onClick={handleComputeField} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Compute Field</button>
            {fieldResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(fieldResult, null, 2)}</pre>
            )}
          </div>

          {/* Predict Trajectory */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Predict Trajectory</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Context ID *</label>
                <input value={predictForm.context_id} onChange={e => setPredictForm({ ...predictForm, context_id: e.target.value })} placeholder="context id" />
              </div>
              <div className="form-group">
                <label>Start Concept *</label>
                <input value={predictForm.start_concept} onChange={e => setPredictForm({ ...predictForm, start_concept: e.target.value })} placeholder="starting concept" />
              </div>
              <div className="form-group">
                <label>Steps</label>
                <input value={predictForm.steps} onChange={e => setPredictForm({ ...predictForm, steps: e.target.value })} type="number" min="1" />
              </div>
              <div className="form-group">
                <label>Step Size</label>
                <input value={predictForm.step_size} onChange={e => setPredictForm({ ...predictForm, step_size: e.target.value })} type="number" min="0" step="0.1" />
              </div>
            </div>
            <button onClick={handlePredictTrajectory} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Predict</button>
            {predictResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(predictResult, null, 2)}</pre>
            )}
          </div>

          {/* Check Escape */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Check Basin Escape</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Trajectory ID *</label>
                <input value={escapeForm.trajectory_id} onChange={e => setEscapeForm({ ...escapeForm, trajectory_id: e.target.value })} placeholder="trajectory id" />
              </div>
            </div>
            <button onClick={handleCheckEscape} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Check Escape</button>
            {escapeResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(escapeResult, null, 2)}</pre>
            )}
          </div>

          {/* Trajectories List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Trajectories ({trajectories.length})</h3>
            <button onClick={() => loadTrajectories()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {trajectories.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No trajectories recorded. Predict one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {trajectories.slice(0, 30).map((t: any, i: number) => {
                  const id = t.trajectory_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{t.start_concept ?? 'unknown_start'} → {t.end_concept ?? 'unknown_end'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>context: {t.context_id ?? '-'} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {t.status && renderBadge(t.status, statusColor(t.status))}
                          {t.field_state && renderBadge(t.field_state, themeColors.secondary)}
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

export default CognitiveGravityPanel;
