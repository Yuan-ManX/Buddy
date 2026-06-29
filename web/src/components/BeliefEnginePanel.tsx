import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#e11d48',
  secondary: '#fb7185',
  bg: '#fff1f2',
  border: '#fecdd3',
  accent: '#ffe4e6',
  text: '#9f1239',
};

const CATEGORIES = ['factual', 'procedural', 'causal', 'temporal', 'spatial', 'social', 'normative', 'intentional', 'abstract'];
const EVIDENCE_TYPES = ['observation', 'testimony', 'inference', 'intuition', 'authority', 'empirical', 'deductive'];
const STRENGTH_LABELS: Record<number, string> = { 0: 'overwhelming', 1: 'strong', 2: 'moderate', 3: 'weak', 4: 'negligible' };

export const BeliefEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'network' | 'belief' | 'revise'>('overview');

  // Shared state
  const [networks, setNetworks] = useState<any[]>([]);
  const [selectedNetworkId, setSelectedNetworkId] = useState<string>('');
  const [beliefs, setBeliefs] = useState<any[]>([]);
  const [selectedBeliefId, setSelectedBeliefId] = useState<string>('');
  const [beliefDetail, setBeliefDetail] = useState<any>(null);

  // Network form (create network)
  const [networkForm, setNetworkForm] = useState({ agent_id: '' });

  // Belief form (add belief to network)
  const [beliefForm, setBeliefForm] = useState({
    proposition: '',
    description: '',
    category: 'factual',
    initial_confidence: '',
  });

  // Evidence form
  const [evidenceForm, setEvidenceForm] = useState({
    evidence_type: 'observation',
    strength: '2',
    content: '',
    source: '',
    reliability: '',
  });
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string>('');

  // Revise form
  const [reviseForm, setReviseForm] = useState({ reasoning: '' });
  const [revisions, setRevisions] = useState<any[]>([]);
  const [consistency, setConsistency] = useState<any>(null);
  const [mostConfident, setMostConfident] = useState<any[]>([]);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.beliefEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load belief engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadNetworks = useCallback(async () => {
    try {
      const result = await api.beliefEngine.listNetworks();
      const list = Array.isArray(result) ? result : (result?.networks ?? []);
      setNetworks(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load networks');
    }
  }, [toast]);

  const loadBeliefs = useCallback(async (networkId: string) => {
    if (!networkId) return;
    try {
      const result = await api.beliefEngine.listBeliefs(networkId);
      const list = Array.isArray(result) ? result : (result?.beliefs ?? []);
      setBeliefs(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load beliefs');
    }
  }, [toast]);

  const loadBeliefDetail = useCallback(async (networkId: string, beliefId: string) => {
    if (!networkId || !beliefId) return;
    try {
      const result = await api.beliefEngine.getBelief(networkId, beliefId);
      setBeliefDetail(result);
      const evList = Array.isArray(result?.evidence) ? result.evidence : (result?.evidence_list ?? []);
      setEvidenceList(evList);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load belief detail');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadNetworks();
    }
  }, [activeSection, loadStats, loadNetworks]);

  // When entering network section, refresh networks list
  useEffect(() => {
    if (activeSection === 'network') loadNetworks();
  }, [activeSection, loadNetworks]);

  // When selected network changes, refresh its beliefs
  useEffect(() => {
    if (selectedNetworkId) loadBeliefs(selectedNetworkId);
  }, [selectedNetworkId, loadBeliefs]);

  // When entering belief section, ensure networks/beliefs loaded
  useEffect(() => {
    if (activeSection === 'belief' && !selectedNetworkId && networks.length > 0) {
      setSelectedNetworkId(networks[0].id ?? networks[0].network_id ?? '');
    }
  }, [activeSection, selectedNetworkId, networks]);

  // When selected belief changes, fetch detail
  useEffect(() => {
    if (selectedNetworkId && selectedBeliefId) loadBeliefDetail(selectedNetworkId, selectedBeliefId);
  }, [selectedNetworkId, selectedBeliefId, loadBeliefDetail]);

  const handleCreateNetwork = async () => {
    if (!networkForm.agent_id.trim()) return;
    try {
      const result = await api.beliefEngine.createNetwork({ agent_id: networkForm.agent_id.trim() });
      toast.success(`Belief network created`);
      setNetworkForm({ agent_id: '' });
      await loadNetworks();
      const newId = result?.id ?? result?.network_id;
      if (newId) setSelectedNetworkId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddBelief = async () => {
    if (!selectedNetworkId || !beliefForm.proposition.trim()) return;
    try {
      await api.beliefEngine.addBelief(selectedNetworkId, {
        proposition: beliefForm.proposition.trim(),
        description: beliefForm.description.trim() || undefined,
        category: beliefForm.category,
        initial_confidence: beliefForm.initial_confidence !== '' ? Number(beliefForm.initial_confidence) : undefined,
      });
      toast.success('Belief added to network');
      setBeliefForm({ proposition: '', description: '', category: 'factual', initial_confidence: '' });
      loadBeliefs(selectedNetworkId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEvidence = async () => {
    if (!evidenceForm.content.trim()) return;
    try {
      const result = await api.beliefEngine.addEvidence({
        evidence_type: evidenceForm.evidence_type,
        strength: Number(evidenceForm.strength),
        content: evidenceForm.content.trim(),
        source: evidenceForm.source.trim() || undefined,
        reliability: evidenceForm.reliability !== '' ? Number(evidenceForm.reliability) : undefined,
      });
      toast.success('Evidence recorded');
      const newId = result?.id ?? result?.evidence_id;
      setEvidenceForm({ evidence_type: 'observation', strength: '2', content: '', source: '', reliability: '' });
      if (newId) setSelectedEvidenceId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLinkEvidence = async () => {
    if (!selectedNetworkId || !selectedBeliefId || !selectedEvidenceId) return;
    try {
      await api.beliefEngine.linkEvidence(selectedNetworkId, selectedBeliefId, selectedEvidenceId);
      toast.success('Evidence linked to belief');
      loadBeliefDetail(selectedNetworkId, selectedBeliefId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRevise = async () => {
    if (!selectedNetworkId || !selectedBeliefId || !selectedEvidenceId) return;
    try {
      await api.beliefEngine.revise(selectedNetworkId, selectedBeliefId, {
        evidence_id: selectedEvidenceId,
        reasoning: reviseForm.reasoning.trim() || undefined,
      });
      toast.success('Belief revised');
      setReviseForm({ reasoning: '' });
      loadBeliefDetail(selectedNetworkId, selectedBeliefId);
      loadRevisions(selectedNetworkId, selectedBeliefId);
    } catch (e: any) { toast.error(e.message); }
  };

  const loadRevisions = async (networkId: string, beliefId: string) => {
    try {
      const result = await api.beliefEngine.getRevisions(networkId, beliefId);
      const list = Array.isArray(result) ? result : (result?.revisions ?? []);
      setRevisions(list);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCheckConsistency = async () => {
    if (!selectedNetworkId) return;
    try {
      const result = await api.beliefEngine.checkConsistency(selectedNetworkId);
      setConsistency(result);
      toast.success('Consistency check complete');
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePropagate = async () => {
    if (!selectedNetworkId || !selectedBeliefId) return;
    try {
      await api.beliefEngine.propagate(selectedNetworkId, selectedBeliefId);
      toast.success('Belief update propagated');
      loadBeliefDetail(selectedNetworkId, selectedBeliefId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMostConfident = async () => {
    if (!selectedNetworkId) return;
    try {
      const result = await api.beliefEngine.mostConfident(selectedNetworkId, { limit: 10 });
      const list = Array.isArray(result) ? result : (result?.beliefs ?? []);
      setMostConfident(list);
    } catch (e: any) { toast.error(e.message); }
  };

  // When entering revise section, load revisions for current belief
  useEffect(() => {
    if (activeSection === 'revise' && selectedNetworkId && selectedBeliefId) {
      loadRevisions(selectedNetworkId, selectedBeliefId);
      handleMostConfident();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSection, selectedNetworkId, selectedBeliefId]);

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🧠 Belief Engine</h2>
          <p className="panel-subtitle">Manage belief networks, evidence, and revision</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading belief engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🧠 Belief Engine</h2>
        <p className="panel-subtitle">Manage belief networks, evidence, and revision</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_networks ?? '-'}</span><span className="stat-label">Networks</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_beliefs ?? '-'}</span><span className="stat-label">Beliefs</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_evidence ?? '-'}</span><span className="stat-label">Evidence</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_revisions ?? '-'}</span><span className="stat-label">Revisions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.consistency_issues ?? '-'}</span><span className="stat-label">Issues</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'network', 'belief', 'revise'] as const).map(s => (
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

      {/* Network selector shared across network/belief/revise sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Network</label>
          <select
            value={selectedNetworkId}
            onChange={e => { setSelectedNetworkId(e.target.value); setSelectedBeliefId(''); setBeliefDetail(null); }}
          >
            <option value="">— Select a network —</option>
            {networks.map((n: any) => {
              const id = n.id ?? n.network_id;
              return <option key={id} value={id}>{n.name ?? n.agent_id ?? id}</option>;
            })}
          </select>
        </div>
      )}

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Belief Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Networks</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_networks ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Beliefs</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_beliefs ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Evidence</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_evidence ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Revisions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_revisions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Confidence</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{typeof stats.avg_confidence === 'number' ? stats.avg_confidence.toFixed(3) : (stats.avg_confidence ?? 0)}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Consistency Issues</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.consistency_issues ?? 0}</div>
              </div>
            </div>

            {/* Breakdowns */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>Beliefs by Status</div>
                {stats.beliefs_by_status && Object.keys(stats.beliefs_by_status).length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 18, color: themeColors.text, fontSize: '0.9rem' }}>
                    {Object.entries(stats.beliefs_by_status).map(([k, v]: any) => <li key={k}>{k}: {v}</li>)}
                  </ul>
                ) : <div style={{ color: '#999', fontSize: '0.85rem' }}>No data</div>}
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>Beliefs by Category</div>
                {stats.beliefs_by_category && Object.keys(stats.beliefs_by_category).length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 18, color: themeColors.text, fontSize: '0.9rem' }}>
                    {Object.entries(stats.beliefs_by_category).map(([k, v]: any) => <li key={k}>{k}: {v}</li>)}
                  </ul>
                ) : <div style={{ color: '#999', fontSize: '0.85rem' }}>No data</div>}
              </div>
            </div>
          </div>

          {/* Existing networks list */}
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Existing Networks</h3>
            {networks.length === 0 ? (
              <div style={{ color: '#999' }}>No networks yet. Create one in the Network tab.</div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10, marginTop: 12 }}>
                {networks.map((n: any) => {
                  const id = n.id ?? n.network_id;
                  return (
                    <div key={id} style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{n.name ?? n.agent_id ?? id}</div>
                      <div style={{ fontSize: '0.8rem', color: '#888' }}>{id}</div>
                      {n.agent_id && <div style={{ fontSize: '0.8rem', color: '#666', marginTop: 4 }}>agent: {n.agent_id}</div>}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Network section: create network + add belief */}
      {activeSection === 'network' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Belief Network</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={networkForm.agent_id}
                onChange={e => setNetworkForm({ agent_id: e.target.value })}
                placeholder="e.g. agent-001"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateNetwork}
              disabled={!networkForm.agent_id.trim()}
            >
              Create Network
            </button>
          </div>

          <h3 style={{ color: themeColors.text }}>Add Belief to Network</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Proposition *</label>
              <input
                type="text"
                value={beliefForm.proposition}
                onChange={e => setBeliefForm(f => ({ ...f, proposition: e.target.value }))}
                placeholder="The statement this belief represents"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={beliefForm.description}
                onChange={e => setBeliefForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Optional longer description"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Category</label>
                <select value={beliefForm.category} onChange={e => setBeliefForm(f => ({ ...f, category: e.target.value }))}>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Initial Confidence (0.0 - 1.0)</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={beliefForm.initial_confidence}
                  onChange={e => setBeliefForm(f => ({ ...f, initial_confidence: e.target.value }))}
                  placeholder="0.5"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddBelief}
              disabled={!selectedNetworkId || !beliefForm.proposition.trim()}
            >
              Add Belief
            </button>
          </div>

          {/* Beliefs list for selected network */}
          <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h4 style={{ color: themeColors.text }}>Beliefs in Network</h4>
            {!selectedNetworkId ? (
              <div style={{ color: '#999' }}>Select a network above.</div>
            ) : beliefs.length === 0 ? (
              <div style={{ color: '#999' }}>No beliefs yet.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                {beliefs.map((b: any) => {
                  const id = b.id ?? b.belief_id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{b.proposition}</div>
                      <div style={{ fontSize: '0.8rem', color: '#666' }}>
                        {id} · {b.category ?? '-'} · {b.status ?? '-'} · conf {(b.confidence ?? b.initial_confidence ?? 0).toFixed?.(3) ?? b.confidence}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Belief section: add evidence + link + detail */}
      {activeSection === 'belief' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Record Evidence</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Evidence Type</label>
                <select value={evidenceForm.evidence_type} onChange={e => setEvidenceForm(f => ({ ...f, evidence_type: e.target.value }))}>
                  {EVIDENCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Strength (0=overwhelming, 4=negligible)</label>
                <select value={evidenceForm.strength} onChange={e => setEvidenceForm(f => ({ ...f, strength: e.target.value }))}>
                  {[0, 1, 2, 3, 4].map(s => <option key={s} value={s}>{s} — {STRENGTH_LABELS[s]}</option>)}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Content *</label>
              <textarea
                rows={3}
                value={evidenceForm.content}
                onChange={e => setEvidenceForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Describe the evidence"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Source</label>
                <input
                  type="text"
                  value={evidenceForm.source}
                  onChange={e => setEvidenceForm(f => ({ ...f, source: e.target.value }))}
                  placeholder="Where the evidence came from"
                />
              </div>
              <div className="form-group">
                <label>Reliability (0.0 - 1.0)</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={evidenceForm.reliability}
                  onChange={e => setEvidenceForm(f => ({ ...f, reliability: e.target.value }))}
                  placeholder="0.8"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddEvidence}
              disabled={!evidenceForm.content.trim()}
            >
              Record Evidence
            </button>
          </div>

          {/* Link evidence to belief */}
          <div className="form-group" style={{ marginBottom: 16 }}>
            <label>Select Belief</label>
            <select value={selectedBeliefId} onChange={e => setSelectedBeliefId(e.target.value)}>
              <option value="">— Select a belief —</option>
              {beliefs.map((b: any) => {
                const id = b.id ?? b.belief_id;
                return <option key={id} value={id}>{b.proposition}</option>;
              })}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 16 }}>
            <label>Select Evidence to Link</label>
            <select value={selectedEvidenceId} onChange={e => setSelectedEvidenceId(e.target.value)}>
              <option value="">— Select evidence —</option>
              {evidenceList.map((ev: any) => {
                const id = ev.id ?? ev.evidence_id;
                return <option key={id} value={id}>{ev.content ?? id}</option>;
              })}
            </select>
          </div>
          <button
            className="btn-primary"
            style={{ background: themeColors.primary, marginBottom: 16 }}
            onClick={handleLinkEvidence}
            disabled={!selectedNetworkId || !selectedBeliefId || !selectedEvidenceId}
          >
            Link Evidence to Belief
          </button>

          {/* Belief detail */}
          {beliefDetail && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Belief Detail</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(beliefDetail, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Revise section */}
      {activeSection === 'revise' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Revise Belief</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Belief</label>
              <select value={selectedBeliefId} onChange={e => setSelectedBeliefId(e.target.value)}>
                <option value="">— Select a belief —</option>
                {beliefs.map((b: any) => {
                  const id = b.id ?? b.belief_id;
                  return <option key={id} value={id}>{b.proposition}</option>;
                })}
              </select>
            </div>
            <div className="form-group">
              <label>Evidence</label>
              <select value={selectedEvidenceId} onChange={e => setSelectedEvidenceId(e.target.value)}>
                <option value="">— Select evidence —</option>
                {evidenceList.map((ev: any) => {
                  const id = ev.id ?? ev.evidence_id;
                  return <option key={id} value={id}>{ev.content ?? id}</option>;
                })}
              </select>
            </div>
          </div>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Reasoning</label>
              <textarea
                rows={3}
                value={reviseForm.reasoning}
                onChange={e => setReviseForm({ reasoning: e.target.value })}
                placeholder="Explain why this revision is being made"
              />
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary }}
                onClick={handleRevise}
                disabled={!selectedNetworkId || !selectedBeliefId || !selectedEvidenceId}
              >
                Submit Revision
              </button>
              <button
                className="btn-primary"
                style={{ background: themeColors.secondary }}
                onClick={handlePropagate}
                disabled={!selectedNetworkId || !selectedBeliefId}
              >
                Propagate Update
              </button>
              <button
                className="btn-primary"
                style={{ background: themeColors.secondary }}
                onClick={handleCheckConsistency}
                disabled={!selectedNetworkId}
              >
                Check Consistency
              </button>
            </div>
          </div>

          {/* Revision history */}
          <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 12 }}>
            <h4 style={{ color: themeColors.text }}>Revision History</h4>
            {revisions.length === 0 ? (
              <div style={{ color: '#999' }}>No revisions recorded.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                {revisions.map((r: any, i: number) => (
                  <div key={r.id ?? r.revision_id ?? i} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                    <div style={{ fontSize: '0.8rem', color: '#888' }}>{r.timestamp ?? r.created_at ?? '-'}</div>
                    <div style={{ color: themeColors.text }}>
                      confidence: {r.prior_confidence ?? '?'} → {r.posterior_confidence ?? '?'}
                    </div>
                    {r.reasoning && <div style={{ fontSize: '0.85rem', color: '#555', marginTop: 4 }}>{r.reasoning}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Consistency result */}
          {consistency && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 12 }}>
              <h4 style={{ color: themeColors.text }}>Consistency Check</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(consistency, null, 2)}</pre>
            </div>
          )}

          {/* Most confident beliefs */}
          <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ color: themeColors.text, margin: 0 }}>Most Confident Beliefs</h4>
              <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={handleMostConfident} disabled={!selectedNetworkId}>
                Refresh
              </button>
            </div>
            {mostConfident.length === 0 ? (
              <div style={{ color: '#999', marginTop: 8 }}>No data. Click Refresh.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                {mostConfident.map((b: any, i: number) => {
                  const id = b.id ?? b.belief_id;
                  return (
                    <div key={id ?? i} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{b.proposition}</div>
                      <div style={{ fontSize: '0.8rem', color: '#666' }}>
                        conf {(b.confidence ?? 0).toFixed?.(3) ?? b.confidence} · {b.category ?? '-'} · {id}
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

export default BeliefEnginePanel;
