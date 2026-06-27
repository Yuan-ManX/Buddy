import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#2563eb',
  secondary: '#60a5fa',
  bg: '#eff6ff',
  border: '#93c5fd',
  accent: '#dbeafe',
  text: '#1e40af',
};

const FUSION_STRATEGIES = [
  'weighted_average', 'best_of_n', 'consensus', 'hierarchical', 'ensemble', 'round_robin',
];

const CONFLICT_RESOLUTIONS = [
  'majority_vote', 'highest_confidence', 'expert_override', 'mediation', 'hybrid',
];

export const SynthesisEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'sessions'>('overview');

  const [createForm, setCreateForm] = useState({
    topic: '', description: '', fusion_strategy: 'weighted_average', conflict_resolution: 'highest_confidence',
  });
  const [creating, setCreating] = useState(false);
  const [sessions, setSessions] = useState<any[] | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.synthesisEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load synthesis engine data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!createForm.topic.trim()) return;
    try {
      setCreating(true);
      const result = await api.synthesisEngine.createSession({
        topic: createForm.topic,
        description: createForm.description || undefined,
        fusion_strategy: createForm.fusion_strategy,
        conflict_resolution: createForm.conflict_resolution,
      });
      toast.success(`Session created: ${result.session_id}`);
      setCreateForm({ topic: '', description: '', fusion_strategy: 'weighted_average', conflict_resolution: 'highest_confidence' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
    finally { setCreating(false); }
  };

  const handleLoadSessions = async () => {
    try {
      const r = await api.synthesisEngine.results(10);
      setSessions(r.results || r);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔗 Collaborative Synthesis Engine</h2>
          <p className="panel-subtitle">Multi-agent output fusion and orchestration</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading synthesis engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔗 Collaborative Synthesis Engine</h2>
        <p className="panel-subtitle">Multi-agent output fusion and orchestration</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_sessions ?? '-'}</span><span className="stat-label">Total Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_syntheses ?? '-'}</span><span className="stat-label">Total Syntheses</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.avg_confidence?.toFixed?.(2) ?? stats.avg_confidence ?? '-'}</span><span className="stat-label">Avg Confidence</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.avg_consensus?.toFixed?.(2) ?? stats.avg_consensus ?? '-'}</span><span className="stat-label">Avg Consensus</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'sessions'] as const).map(s => (
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

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Synthesis Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.active_sessions ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Results</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_results ?? 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Session */}
      {activeSection === 'create' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Synthesis Session</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Topic</label>
              <input
                type="text"
                value={createForm.topic}
                onChange={e => setCreateForm(f => ({ ...f, topic: e.target.value }))}
                placeholder="Enter the synthesis topic..."
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={createForm.description}
                onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the synthesis goal..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Fusion Strategy</label>
                <select value={createForm.fusion_strategy} onChange={e => setCreateForm(f => ({ ...f, fusion_strategy: e.target.value }))}>
                  {FUSION_STRATEGIES.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Conflict Resolution</label>
                <select value={createForm.conflict_resolution} onChange={e => setCreateForm(f => ({ ...f, conflict_resolution: e.target.value }))}>
                  {CONFLICT_RESOLUTIONS.map(c => (
                    <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreate}
              disabled={creating || !createForm.topic.trim()}
            >
              {creating ? 'Creating...' : '🔗 Create Session'}
            </button>
          </div>
        </div>
      )}

      {/* Sessions */}
      {activeSection === 'sessions' && (
        <div className="dashboard-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Recent Sessions</h3>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleLoadSessions}>Load Sessions</button>
          </div>
          {sessions ? (
            sessions.length === 0 ? (
              <div className="panel-empty">No synthesis sessions yet</div>
            ) : (
              <div className="forge-skill-list">
                {sessions.map((s: any, idx: number) => (
                  <div key={s.result_id || s.session_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                    <div className="forge-skill-header">
                      <div className="forge-skill-name" style={{ color: themeColors.text }}>{s.topic || s.result_id}</div>
                      <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                        {s.confidence != null ? `${(s.confidence * 100).toFixed?.(0) ?? s.confidence}%` : '-'}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      <div style={{ color: themeColors.text, marginBottom: 4 }}>{s.final_content?.slice(0, 200) || s.topic}</div>
                      <div>Quality: {s.quality_score?.toFixed?.(2) ?? '-'} | Consensus: {s.consensus_level?.toFixed?.(2) ?? '-'}</div>
                      {s.contributors?.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          {s.contributors.map((c: string) => (
                            <span key={c} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{c}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="panel-empty">Click "Load Sessions" to view recent synthesis sessions</div>
          )}
        </div>
      )}
    </div>
  );
};

export default SynthesisEnginePanel;