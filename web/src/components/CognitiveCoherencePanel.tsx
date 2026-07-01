import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: blue for cognitive coherence
const themeColors = {
  primary: '#2563eb',
  secondary: '#3b82f6',
  bg: '#eff6ff',
  border: '#bfdbfe',
  accent: '#dbeafe',
  text: '#1e3a8a',
};

// Enum values must match backend CoherenceFacet / CoherenceRegime / RelationType / RepairStrategy / CoherenceTrajectory exactly (uppercase).
const COHERENCE_FACETS = ['EXPLANATORY', 'LOGICAL', 'TELEOLOGICAL', 'NARRATIVE', 'CONCEPTUAL', 'EPISTEMIC'];
const COHERENCE_REGIMES = ['FRAGMENTED', 'LOOSE', 'PARTIAL', 'COHERENT', 'INTEGRATED', 'UNIFIED'];
const RELATION_TYPES = ['SUPPORTS', 'CONTRADICTS', 'EXPLAINS', 'ENABLES', 'CONFLICTS', 'COHERES_WITH'];
const REPAIR_STRATEGIES = ['RESOLVE_CONTRADICTION', 'ADD_BRIDGE', 'REWEIGHT', 'REMOVE_NODE', 'SPLIT_CONTEXT', 'REFRAME'];
const COHERENCE_TRAJECTORIES = ['STABILIZING', 'STABLE', 'DESTABILIZING', 'FLUCTUATING', 'COLLAPSING', 'CONSOLIDATING'];

// Map a coherence regime value to a badge color for at-a-glance scanning.
const STATUS_COLORS: Record<string, string> = {
  FRAGMENTED: '#dc2626',
  LOOSE: '#f97316',
  PARTIAL: '#f59e0b',
  COHERENT: '#0ea5e9',
  INTEGRATED: '#059669',
  UNIFIED: '#16a34a',
};

export const CognitiveCoherencePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'node' | 'repair'>('overview');

  // Nodes / relations / repairs
  const [nodes, setNodes] = useState<any[]>([]);
  const [relations, setRelations] = useState<any[]>([]);
  const [repairs, setRepairs] = useState<any[]>([]);
  const [trajectoryResult, setTrajectoryResult] = useState<any>(null);

  // Register node form
  const [nodeForm, setNodeForm] = useState({
    agent_id: '',
    content: '',
    facet: 'LOGICAL',
    weight: '',
  });

  // Link relation form
  const [relationForm, setRelationForm] = useState({
    agent_id: '',
    source_node_id: '',
    target_node_id: '',
    relation_type: 'SUPPORTS',
    strength: '',
  });

  // Attempt repair form
  const [repairForm, setRepairForm] = useState({
    agent_id: '',
    contradiction_id: '',
    strategy: 'RESOLVE_CONTRADICTION',
    rationale: '',
  });

  // Record trajectory form
  const [trajectoryForm, setTrajectoryForm] = useState({
    agent_id: '',
    trajectory: 'STABILIZING',
    coherence_score: '',
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const s = await api.cognitiveCoherence.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cognitive coherence stats');
    } finally {
      setLoading(false);
    }
  };

  const loadNodes = async () => {
    try {
      const result = await api.cognitiveCoherence.listNodes();
      const list = Array.isArray(result) ? result : (result?.nodes ?? []);
      setNodes(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load nodes');
    }
  };

  const loadRelations = async () => {
    try {
      const result = await api.cognitiveCoherence.listRelations();
      const list = Array.isArray(result) ? result : (result?.relations ?? []);
      setRelations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load relations');
    }
  };

  const loadRepairs = async () => {
    try {
      const result = await api.cognitiveCoherence.listRepairs();
      const list = Array.isArray(result) ? result : (result?.repairs ?? []);
      setRepairs(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load repairs');
    }
  };

  // Initial load
  useEffect(() => { loadStats(); }, []);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadNodes();
      loadRelations();
      loadRepairs();
    }
  }, [activeSection]);

  const handleRegisterNode = async () => {
    if (!nodeForm.agent_id.trim() || !nodeForm.content.trim()) {
      toast.error('Agent ID and content are required');
      return;
    }
    const payload: any = {
      agent_id: nodeForm.agent_id.trim(),
      content: nodeForm.content.trim(),
      facet: nodeForm.facet,
    };
    if (nodeForm.weight.trim()) payload.weight = Number(nodeForm.weight);
    try {
      await api.cognitiveCoherence.registerNode(payload);
      toast.success('Node registered');
      setNodeForm({ agent_id: '', content: '', facet: 'LOGICAL', weight: '' });
      await loadNodes();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLinkRelation = async () => {
    if (!relationForm.agent_id.trim() || !relationForm.source_node_id.trim() || !relationForm.target_node_id.trim()) {
      toast.error('Agent ID and both node IDs are required');
      return;
    }
    const payload: any = {
      agent_id: relationForm.agent_id.trim(),
      source_node_id: relationForm.source_node_id.trim(),
      target_node_id: relationForm.target_node_id.trim(),
      relation_type: relationForm.relation_type,
    };
    if (relationForm.strength.trim()) payload.strength = Number(relationForm.strength);
    try {
      await api.cognitiveCoherence.linkRelation(payload);
      toast.success('Relation linked');
      setRelationForm({ agent_id: '', source_node_id: '', target_node_id: '', relation_type: 'SUPPORTS', strength: '' });
      await loadRelations();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAttemptRepair = async () => {
    if (!repairForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    const payload: any = {
      agent_id: repairForm.agent_id.trim(),
      strategy: repairForm.strategy,
    };
    if (repairForm.contradiction_id.trim()) payload.contradiction_id = repairForm.contradiction_id.trim();
    if (repairForm.rationale.trim()) payload.rationale = repairForm.rationale.trim();
    try {
      await api.cognitiveCoherence.attemptRepair(payload);
      toast.success('Repair attempted');
      setRepairForm({ agent_id: '', contradiction_id: '', strategy: 'RESOLVE_CONTRADICTION', rationale: '' });
      await loadRepairs();
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
    if (trajectoryForm.coherence_score.trim()) payload.coherence_score = Number(trajectoryForm.coherence_score);
    try {
      const result = await api.cognitiveCoherence.recordTrajectory(payload);
      setTrajectoryResult(result);
      toast.success('Trajectory recorded');
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
          <h2>🧩 Cognitive Coherence</h2>
          <p className="panel-subtitle">Register nodes, link relations, and repair contradictions in the belief graph</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cognitive coherence...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧩 Cognitive Coherence</h2>
        <p className="panel-subtitle">Register nodes, link relations, and repair contradictions in the belief graph</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_nodes ?? '-'}</span><span className="stat-label">Nodes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_relations ?? '-'}</span><span className="stat-label">Relations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_snapshots ?? '-'}</span><span className="stat-label">Snapshots</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_repairs ?? '-'}</span><span className="stat-label">Repairs</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_trajectories ?? '-'}</span><span className="stat-label">Trajectories</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_coherence ?? '-'}</span><span className="stat-label">Avg Coherence</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'node', 'repair'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Coherence Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Nodes</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_nodes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Relations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_relations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Snapshots</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_snapshots ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Repairs</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_repairs ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Trajectories</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_trajectories ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Coherence</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.avg_coherence ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Nodes</h3>
            <button onClick={() => loadNodes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {nodes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No nodes registered. Register one in the Node section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {nodes.slice(0, 10).map((n: any, i: number) => {
                  const id = n.node_id ?? n.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {n.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>node {id}{n.content ? ` · ${n.content}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {n.facet && renderBadge(n.facet, themeColors.secondary)}
                          {n.weight != null && renderBadge(`weight: ${n.weight}`, themeColors.primary)}
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

      {/* Node Section */}
      {activeSection === 'node' && (
        <div className="dashboard-section">
          {/* Register Node */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Node</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={nodeForm.agent_id} onChange={e => setNodeForm({ ...nodeForm, agent_id: e.target.value })} placeholder="e.g. agent_42" />
              </div>
              <div className="form-group">
                <label>Facet</label>
                <select value={nodeForm.facet} onChange={e => setNodeForm({ ...nodeForm, facet: e.target.value })}>
                  {COHERENCE_FACETS.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Weight</label>
                <input value={nodeForm.weight} onChange={e => setNodeForm({ ...nodeForm, weight: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Content *</label>
                <input value={nodeForm.content} onChange={e => setNodeForm({ ...nodeForm, content: e.target.value })} placeholder="e.g. free will exists" />
              </div>
            </div>
            <button onClick={handleRegisterNode} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Node</button>
          </div>

          {/* Link Relation */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Link Relation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={relationForm.agent_id} onChange={e => setRelationForm({ ...relationForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Source Node ID *</label>
                <input value={relationForm.source_node_id} onChange={e => setRelationForm({ ...relationForm, source_node_id: e.target.value })} placeholder="source node id" />
              </div>
              <div className="form-group">
                <label>Target Node ID *</label>
                <input value={relationForm.target_node_id} onChange={e => setRelationForm({ ...relationForm, target_node_id: e.target.value })} placeholder="target node id" />
              </div>
              <div className="form-group">
                <label>Relation Type</label>
                <select value={relationForm.relation_type} onChange={e => setRelationForm({ ...relationForm, relation_type: e.target.value })}>
                  {RELATION_TYPES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strength</label>
                <input value={relationForm.strength} onChange={e => setRelationForm({ ...relationForm, strength: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.8" />
              </div>
            </div>
            <button onClick={handleLinkRelation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Link Relation</button>
          </div>

          {/* Nodes List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Nodes ({nodes.length})</h3>
            <button onClick={() => loadNodes()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {nodes.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No nodes registered. Register one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {nodes.slice(0, 30).map((n: any, i: number) => {
                  const id = n.node_id ?? n.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {n.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>node {id}{n.content ? ` · ${n.content}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {n.facet && renderBadge(n.facet, themeColors.secondary)}
                          {n.weight != null && renderBadge(`weight: ${n.weight}`, themeColors.primary)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Relations List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Relations ({relations.length})</h3>
            <button onClick={() => loadRelations()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {relations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No relations linked. Link one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {relations.slice(0, 30).map((r: any, i: number) => {
                  const id = r.relation_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>relation {id}{r.source_node_id ? ` · ${r.source_node_id}` : ''}{r.target_node_id ? ` -> ${r.target_node_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.relation_type && renderBadge(r.relation_type, themeColors.secondary)}
                          {r.strength != null && renderBadge(`strength: ${r.strength}`, themeColors.primary)}
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

      {/* Repair Section */}
      {activeSection === 'repair' && (
        <div className="dashboard-section">
          {/* Attempt Repair */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Attempt Repair</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={repairForm.agent_id} onChange={e => setRepairForm({ ...repairForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Contradiction ID</label>
                <input value={repairForm.contradiction_id} onChange={e => setRepairForm({ ...repairForm, contradiction_id: e.target.value })} placeholder="optional contradiction id" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={repairForm.strategy} onChange={e => setRepairForm({ ...repairForm, strategy: e.target.value })}>
                  {REPAIR_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Rationale</label>
                <input value={repairForm.rationale} onChange={e => setRepairForm({ ...repairForm, rationale: e.target.value })} placeholder="optional rationale" />
              </div>
            </div>
            <button onClick={handleAttemptRepair} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Attempt Repair</button>
          </div>

          {/* Record Trajectory */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Record Trajectory</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={trajectoryForm.agent_id} onChange={e => setTrajectoryForm({ ...trajectoryForm, agent_id: e.target.value })} placeholder="agent id" />
              </div>
              <div className="form-group">
                <label>Trajectory</label>
                <select value={trajectoryForm.trajectory} onChange={e => setTrajectoryForm({ ...trajectoryForm, trajectory: e.target.value })}>
                  {COHERENCE_TRAJECTORIES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Coherence Score</label>
                <input value={trajectoryForm.coherence_score} onChange={e => setTrajectoryForm({ ...trajectoryForm, coherence_score: e.target.value })} type="number" min="0" max="1" step="0.01" placeholder="e.g. 0.7" />
              </div>
            </div>
            <button onClick={handleRecordTrajectory} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Record Trajectory</button>
            {trajectoryResult && (
              <pre style={{ background: themeColors.accent, padding: 8, borderRadius: 4, marginTop: 8, overflow: 'auto', maxHeight: 160, fontSize: 11 }}>{JSON.stringify(trajectoryResult, null, 2)}</pre>
            )}
          </div>

          {/* Repairs List */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Repairs ({repairs.length})</h3>
            <button onClick={() => loadRepairs()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {repairs.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No repairs attempted. Attempt one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {repairs.slice(0, 30).map((r: any, i: number) => {
                  const id = r.repair_id ?? r.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>agent: {r.agent_id ?? '-'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>repair {id}{r.contradiction_id ? ` · contradiction: ${r.contradiction_id}` : ''}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {r.strategy && renderBadge(r.strategy, themeColors.secondary)}
                          {r.regime && renderBadge(r.regime, statusColor(r.regime))}
                        </div>
                      </div>
                      {r.rationale && (
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7, marginTop: 4 }}>{r.rationale}</div>
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

export default CognitiveCoherencePanel;
