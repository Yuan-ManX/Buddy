import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: emerald for cognitive lattice
const themeColors = {
  primary: '#059669',
  secondary: '#34d399',
  bg: '#ecfdf5',
  border: '#a7f3d0',
  accent: '#d1fae5',
  text: '#064e3b',
};

// Enum values must match backend NodeType / StructureSignature / LatticeRegime / FormationStrategy / RefinementAction exactly (uppercase).
const NODE_TYPES = ['CONCEPT', 'SCHEMA', 'FRAME', 'PRINCIPLE', 'HEURISTIC', 'METAPHOR'];
const STRUCTURE_SIGNATURES = ['RANDOM', 'SCALE_FREE', 'SMALL_WORLD', 'REGULAR', 'HIERARCHICAL', 'MODULAR'];
const FORMATION_STRATEGIES = ['CONNECT', 'PRUNE', 'RESTRUCTURE', 'CLUSTER', 'HIERARCHIZE', 'STABILIZE'];
const REFINEMENT_ACTIONS = ['ADD_EDGE', 'REMOVE_EDGE', 'REWEIGHT', 'MERGE', 'SPLIT', 'RELABEL'];

// Map a structure signature value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  RANDOM: '#6b7280',
  SCALE_FREE: '#0ea5e9',
  SMALL_WORLD: '#10b981',
  REGULAR: '#a855f7',
  HIERARCHICAL: '#f59e0b',
  MODULAR: '#ec4899',
};

export const CognitiveLatticePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'readings' | 'edges' | 'snapshots' | 'plans' | 'refinements'>('overview');

  // Readings / edges / snapshots / plans / refinements
  const [readings, setReadings] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [refinements, setRefinements] = useState<any[]>([]);
  const [snapshotResult, setSnapshotResult] = useState<any>(null);

  // Record reading form
  const [readingForm, setReadingForm] = useState({
    agent_id: '',
    node_type: 'CONCEPT',
    order_score: '',
    connectivity: '',
    structure_signature: 'SMALL_WORLD',
    intensity: '',
    notes: '',
  });

  // Record edge form
  const [edgeForm, setEdgeForm] = useState({
    agent_id: '',
    source_node: '',
    target_node: '',
    weight: '',
    relation: '',
    notes: '',
  });

  // Take snapshot form
  const [snapshotForm, setSnapshotForm] = useState({
    agent_id: '',
  });

  // Plan formation form
  const [planForm, setPlanForm] = useState({
    agent_id: '',
    strategy: 'CONNECT',
    target_order: '',
    rationale: '',
  });

  // Record refinement form
  const [refinementForm, setRefinementForm] = useState({
    agent_id: '',
    action: 'ADD_EDGE',
    nodes_affected: '',
    before_score: '',
    after_score: '',
    notes: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveLattice.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive lattice stats');
    } finally {
      setLoading(false);
    }
  };

  const loadReadings = async () => {
    try {
      const result = await api.cognitiveLattice.listReadings();
      const list = Array.isArray(result) ? result : (result?.readings ?? []);
      setReadings(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load readings');
    }
  };

  const loadEdges = async () => {
    try {
      const result = await api.cognitiveLattice.listEdges();
      const list = Array.isArray(result) ? result : (result?.edges ?? []);
      setEdges(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load edges');
    }
  };

  const loadSnapshots = async () => {
    try {
      const result = await api.cognitiveLattice.listSnapshots();
      const list = Array.isArray(result) ? result : (result?.snapshots ?? []);
      setSnapshots(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load snapshots');
    }
  };

  const loadPlans = async () => {
    try {
      const result = await api.cognitiveLattice.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  };

  const loadRefinements = async () => {
    try {
      const result = await api.cognitiveLattice.listRefinements();
      const list = Array.isArray(result) ? result : (result?.refinements ?? []);
      setRefinements(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load refinements');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadReadings();
      loadEdges();
      loadSnapshots();
      loadPlans();
      loadRefinements();
    }
  }, [activeSection]);

  const handleRecordReading = async () => {
    if (!readingForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: readingForm.agent_id.trim(),
      node_type: readingForm.node_type,
      order_score: readingForm.order_score.trim() === '' ? 0.5 : Number(readingForm.order_score),
      connectivity: readingForm.connectivity.trim() === '' ? 0 : Number(readingForm.connectivity),
      structure_signature: readingForm.structure_signature,
      intensity: readingForm.intensity.trim() === '' ? 0.5 : Number(readingForm.intensity),
    };
    if (readingForm.notes) payload.notes = readingForm.notes.trim();
    try {
      await api.cognitiveLattice.recordReading(payload);
      toast.success('Reading recorded');
      setReadingForm({ agent_id: '', node_type: 'CONCEPT', order_score: '', connectivity: '', structure_signature: 'SMALL_WORLD', intensity: '', notes: '' });
      await loadReadings();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordEdge = async () => {
    if (!edgeForm.agent_id.trim() || !edgeForm.source_node.trim() || !edgeForm.target_node.trim() || !edgeForm.relation.trim()) {
      toast.error('Agent ID, source, target, and relation are required');
      return;
    }
    const payload: any = {
      agent_id: edgeForm.agent_id.trim(),
      source_node: edgeForm.source_node.trim(),
      target_node: edgeForm.target_node.trim(),
      weight: edgeForm.weight.trim() === '' ? 0 : Number(edgeForm.weight),
      relation: edgeForm.relation.trim(),
    };
    if (edgeForm.notes) payload.notes = edgeForm.notes.trim();
    try {
      await api.cognitiveLattice.recordEdge(payload);
      toast.success('Edge recorded');
      setEdgeForm({ agent_id: '', source_node: '', target_node: '', weight: '', relation: '', notes: '' });
      await loadEdges();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleTakeSnapshot = async () => {
    if (!snapshotForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      const result = await api.cognitiveLattice.takeSnapshot({ agent_id: snapshotForm.agent_id.trim() });
      setSnapshotResult(result);
      toast.success('Snapshot taken');
      await loadSnapshots();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePlanFormation = async () => {
    if (!planForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: planForm.agent_id.trim(),
      strategy: planForm.strategy,
      target_order: planForm.target_order.trim() === '' ? 0 : Number(planForm.target_order),
      rationale: planForm.rationale.trim(),
    };
    try {
      await api.cognitiveLattice.planFormation(payload);
      toast.success('Formation plan created');
      setPlanForm({ agent_id: '', strategy: 'CONNECT', target_order: '', rationale: '' });
      await loadPlans();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordRefinement = async () => {
    if (!refinementForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: refinementForm.agent_id.trim(),
      action: refinementForm.action,
      nodes_affected: refinementForm.nodes_affected.trim() === '' ? 0 : Number(refinementForm.nodes_affected),
      before_score: refinementForm.before_score.trim() === '' ? 0 : Number(refinementForm.before_score),
      after_score: refinementForm.after_score.trim() === '' ? 0 : Number(refinementForm.after_score),
    };
    if (refinementForm.notes) payload.notes = refinementForm.notes.trim();
    try {
      await api.cognitiveLattice.recordRefinement(payload);
      toast.success('Refinement recorded');
      setRefinementForm({ agent_id: '', action: 'ADD_EDGE', nodes_affected: '', before_score: '', after_score: '', notes: '' });
      await loadRefinements();
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
          <h2>💎 Cognitive Lattice</h2>
          <p className="panel-subtitle">Map structure, record edges, and refine the cognitive lattice network</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive lattice...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💎 Cognitive Lattice</h2>
        <p className="panel-subtitle">Map structure, record edges, and refine the cognitive lattice network</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_agents ?? '-'}</span><span className="stat-label">Agents</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_readings ?? '-'}</span><span className="stat-label">Readings</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_edges ?? '-'}</span><span className="stat-label">Edges</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_order ?? '-'}</span><span className="stat-label">Avg Order</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</span><span className="stat-label">Dominant Regime</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'readings', 'edges', 'snapshots', 'plans', 'refinements'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Lattice Overview</h3>
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
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Edges</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_edges ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Order</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_order ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Dominant Regime</div>
                <div style={{ fontSize: 18, color: themeColors.primary }}>{stats.dominant_regime ?? '-'}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Readings</h3>
            <button onClick={() => loadReadings()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {readings.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No readings recorded. Record one in the Readings section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {readings.slice(0, 10).map((r: any, i: number) => {
                  const id = r.reading_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.node_type ? ` · ${r.node_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.node_type && renderBadge(r.node_type, themeColors.secondary)}
                          {r.structure_signature && renderBadge(r.structure_signature, statusColor(r.structure_signature))}
                          {typeof r.order_score !== 'undefined' && renderBadge(`order ${r.order_score}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Edges</h3>
            <button onClick={() => loadEdges()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {edges.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No edges recorded. Record one in the Edges section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {edges.slice(0, 10).map((e: any, i: number) => {
                  const id = e.edge_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>edge {id}{e.relation ? ` · ${e.relation}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.source_node && e.target_node && renderBadge(`${e.source_node}->${e.target_node}`, themeColors.secondary)}
                          {typeof e.weight !== 'undefined' && renderBadge(`w ${e.weight}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Refinements</h3>
            <button onClick={() => loadRefinements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {refinements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No refinements recorded. Record one in the Refinements section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {refinements.slice(0, 10).map((r: any, i: number) => {
                  const id = r.refinement_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>refinement {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.action && renderBadge(r.action, themeColors.secondary)}
                          {typeof r.nodes_affected !== 'undefined' && renderBadge(`nodes ${r.nodes_affected}`, themeColors.primary)}
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

      {/* Readings Section */}
      {activeSection === 'readings' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Reading</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={readingForm.agent_id} onChange={e => setReadingForm({ ...readingForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Node Type</label>
                <select className="form-select" value={readingForm.node_type} onChange={e => setReadingForm({ ...readingForm, node_type: e.target.value })}>
                  {NODE_TYPES.map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Structure Signature</label>
                <select className="form-select" value={readingForm.structure_signature} onChange={e => setReadingForm({ ...readingForm, structure_signature: e.target.value })}>
                  {STRUCTURE_SIGNATURES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Order Score</label>
                <input className="form-input" value={readingForm.order_score} onChange={e => setReadingForm({ ...readingForm, order_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.6" />
              </div>
              <div className="form-group">
                <label>Connectivity</label>
                <input className="form-input" value={readingForm.connectivity} onChange={e => setReadingForm({ ...readingForm, connectivity: e.target.value })} type="number" min="0" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>Intensity</label>
                <input className="form-input" value={readingForm.intensity} onChange={e => setReadingForm({ ...readingForm, intensity: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.5" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={readingForm.notes} onChange={e => setReadingForm({ ...readingForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordReading} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Reading</button>
          </div>

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
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>reading {id}{r.node_type ? ` · ${r.node_type}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.node_type && renderBadge(r.node_type, themeColors.secondary)}
                          {r.structure_signature && renderBadge(r.structure_signature, statusColor(r.structure_signature))}
                          {typeof r.order_score !== 'undefined' && renderBadge(`order ${r.order_score}`, themeColors.primary)}
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

      {/* Edges Section */}
      {activeSection === 'edges' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Edge</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={edgeForm.agent_id} onChange={e => setEdgeForm({ ...edgeForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Source Node *</label>
                <input className="form-input" value={edgeForm.source_node} onChange={e => setEdgeForm({ ...edgeForm, source_node: e.target.value })} placeholder="source node" />
              </div>
              <div className="form-group">
                <label>Target Node *</label>
                <input className="form-input" value={edgeForm.target_node} onChange={e => setEdgeForm({ ...edgeForm, target_node: e.target.value })} placeholder="target node" />
              </div>
              <div className="form-group">
                <label>Weight</label>
                <input className="form-input" value={edgeForm.weight} onChange={e => setEdgeForm({ ...edgeForm, weight: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Relation *</label>
                <input className="form-input" value={edgeForm.relation} onChange={e => setEdgeForm({ ...edgeForm, relation: e.target.value })} placeholder="e.g. supports" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={edgeForm.notes} onChange={e => setEdgeForm({ ...edgeForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordEdge} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Edge</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Edges ({edges.length})</h3>
            <button onClick={() => loadEdges()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {edges.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No edges recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {edges.slice(0, 30).map((e: any, i: number) => {
                  const id = e.edge_id ?? e.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {e.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>edge {id}{e.relation ? ` · ${e.relation}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {e.source_node && e.target_node && renderBadge(`${e.source_node}->${e.target_node}`, themeColors.secondary)}
                          {typeof e.weight !== 'undefined' && renderBadge(`w ${e.weight}`, themeColors.primary)}
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

      {/* Snapshots Section */}
      {activeSection === 'snapshots' && (
        <div className="dashboard-section">
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

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Snapshots ({snapshots.length})</h3>
            <button onClick={() => loadSnapshots()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {snapshots.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No snapshots taken. Take one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {snapshots.slice(0, 30).map((s: any, i: number) => {
                  const id = s.snapshot_id ?? s.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {s.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>snapshot {id}</div>
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
        </div>
      )}

      {/* Plans Section */}
      {activeSection === 'plans' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Plan Formation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={planForm.agent_id} onChange={e => setPlanForm({ ...planForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select className="form-select" value={planForm.strategy} onChange={e => setPlanForm({ ...planForm, strategy: e.target.value })}>
                  {FORMATION_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Order</label>
                <input className="form-input" value={planForm.target_order} onChange={e => setPlanForm({ ...planForm, target_order: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input className="form-input" value={planForm.rationale} onChange={e => setPlanForm({ ...planForm, rationale: e.target.value })} placeholder="rationale for plan" />
              </div>
            </div>
            <button onClick={handlePlanFormation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Plan Formation</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Plans ({plans.length})</h3>
            <button onClick={() => loadPlans()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {plans.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No plans created. Create one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {plans.slice(0, 30).map((p: any, i: number) => {
                  const id = p.plan_id ?? p.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {p.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>plan {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {p.strategy && renderBadge(p.strategy, themeColors.secondary)}
                          {typeof p.target_order !== 'undefined' && renderBadge(`order ${p.target_order}`, themeColors.primary)}
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

      {/* Refinements Section */}
      {activeSection === 'refinements' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Refinement</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input className="form-input" value={refinementForm.agent_id} onChange={e => setRefinementForm({ ...refinementForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Action</label>
                <select className="form-select" value={refinementForm.action} onChange={e => setRefinementForm({ ...refinementForm, action: e.target.value })}>
                  {REFINEMENT_ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Nodes Affected</label>
                <input className="form-input" value={refinementForm.nodes_affected} onChange={e => setRefinementForm({ ...refinementForm, nodes_affected: e.target.value })} type="number" min="0" step="1" placeholder="e.g. 3" />
              </div>
              <div className="form-group">
                <label>Before Score</label>
                <input className="form-input" value={refinementForm.before_score} onChange={e => setRefinementForm({ ...refinementForm, before_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.4" />
              </div>
              <div className="form-group">
                <label>After Score</label>
                <input className="form-input" value={refinementForm.after_score} onChange={e => setRefinementForm({ ...refinementForm, after_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <input className="form-input" value={refinementForm.notes} onChange={e => setRefinementForm({ ...refinementForm, notes: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRecordRefinement} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Refinement</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Refinements ({refinements.length})</h3>
            <button onClick={() => loadRefinements()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {refinements.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No refinements recorded. Record one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {refinements.slice(0, 30).map((r: any, i: number) => {
                  const id = r.refinement_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>refinement {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.action && renderBadge(r.action, themeColors.secondary)}
                          {typeof r.nodes_affected !== 'undefined' && renderBadge(`nodes ${r.nodes_affected}`, themeColors.primary)}
                          {typeof r.before_score !== 'undefined' && r.after_score !== 'undefined' && renderBadge(`${r.before_score}->${r.after_score}`, themeColors.secondary)}
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

export default CognitiveLatticePanel;
