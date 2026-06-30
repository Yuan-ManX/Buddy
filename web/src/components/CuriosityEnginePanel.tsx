import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: green for curiosity engine
const themeColors = {
  primary: '#16a34a',
  secondary: '#22c55e',
  bg: '#f0fdf4',
  border: '#bbf7d0',
  accent: '#dcfce7',
  text: '#14532d',
};

// Enum values must match backend CuriosityType / NoveltyMetric / ExplorationMode / CuriosityStatus exactly (lowercase).
const CURIOSITY_TYPES = ['diversive', 'specific', 'perceptual', 'epistemic', 'social'];
const NOVELTY_METRICS = ['euclidean', 'cosine', 'entropy', 'frequency', 'recency'];
const EXPLORATION_MODES = ['exploitation', 'balanced', 'exploration', 'forced_exploration'];
const CURIOSITY_STATUS = ['idle', 'seeking', 'exploring', 'satisfied', 'sated'];
const INFO_GAP_TYPES = ['known_unknown', 'unknown_unknown', 'partial_knowledge', 'conflicting_knowledge'];

// Urgency is not a backend enum but drives badge color for info gaps.
const URGENCY_LEVELS = ['low', 'medium', 'high', 'critical'];

const STATUS_COLORS: Record<string, string> = {
  idle: '#9ca3af',
  seeking: '#2563eb',
  exploring: '#d97706',
  satisfied: '#059669',
  sated: '#7c3aed',
};

const URGENCY_COLORS: Record<string, string> = {
  low: '#9ca3af',
  medium: '#d97706',
  high: '#ea580c',
  critical: '#dc2626',
};

export const CuriosityEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'gap' | 'explore'>('overview');

  // Gaps / targets / results / mode
  const [gaps, setGaps] = useState<any[]>([]);
  const [targets, setTargets] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [currentMode, setCurrentMode] = useState<string>('balanced');
  const [agentId] = useState<string>('default');

  // Gap form
  const [gapForm, setGapForm] = useState({
    gap_type: 'known_unknown',
    topic: '',
    urgency: 'medium',
    description: '',
  });

  // Target form
  const [targetForm, setTargetForm] = useState({
    curiosity_type: 'specific',
    novelty_metric: 'cosine',
    description: '',
    expected_info_gain: '',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.curiosityEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load curiosity engine stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadGaps = useCallback(async () => {
    try {
      const result = await api.curiosityEngine.listGaps();
      const list = Array.isArray(result) ? result : (result?.gaps ?? []);
      setGaps(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load info gaps');
    }
  }, [toast]);

  const loadTargets = useCallback(async () => {
    try {
      const result = await api.curiosityEngine.listTargets();
      const list = Array.isArray(result) ? result : (result?.targets ?? []);
      setTargets(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load exploration targets');
    }
  }, [toast]);

  const loadResults = useCallback(async () => {
    try {
      const result = await api.curiosityEngine.listResults();
      const list = Array.isArray(result) ? result : (result?.results ?? []);
      setResults(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load exploration results');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + lists when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadGaps();
      loadTargets();
    }
  }, [activeSection, loadStats, loadGaps, loadTargets]);

  const handleIdentifyGap = async () => {
    if (!gapForm.topic.trim()) {
      toast.error('Topic is required');
      return;
    }
    try {
      const payload: any = {
        gap_type: gapForm.gap_type,
        topic: gapForm.topic.trim(),
        urgency: gapForm.urgency,
      };
      if (gapForm.description.trim()) payload.description = gapForm.description.trim();
      await api.curiosityEngine.identifyGap(payload);
      toast.success('Information gap identified');
      setGapForm({ gap_type: 'known_unknown', topic: '', urgency: 'medium', description: '' });
      await loadGaps();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleResolveGap = async (gapId: string) => {
    try {
      await api.curiosityEngine.resolveGap(gapId, 'resolved');
      toast.success('Gap resolved');
      await loadGaps();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleProposeTarget = async () => {
    if (!targetForm.description.trim()) {
      toast.error('Description is required');
      return;
    }
    try {
      const payload: any = {
        curiosity_type: targetForm.curiosity_type,
        novelty_metric: targetForm.novelty_metric,
        description: targetForm.description.trim(),
      };
      if (targetForm.expected_info_gain.trim() !== '') {
        payload.expected_info_gain = Number(targetForm.expected_info_gain);
      }
      await api.curiosityEngine.proposeTarget(payload);
      toast.success('Exploration target proposed');
      setTargetForm({ curiosity_type: 'specific', novelty_metric: 'cosine', description: '', expected_info_gain: '' });
      await loadTargets();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSelectTarget = async (targetId: string) => {
    try {
      await api.curiosityEngine.selectTarget(targetId);
      toast.success('Target selected for exploration');
      await loadTargets();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSetMode = async () => {
    try {
      await api.curiosityEngine.setMode(agentId, currentMode);
      toast.success(`Exploration mode set to ${currentMode}`);
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
  const urgencyColor = (u: string) => URGENCY_COLORS[u] ?? themeColors.primary;

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔍 Curiosity Engine</h2>
          <p className="panel-subtitle">Identify information gaps and propose exploration targets</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading curiosity engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔍 Curiosity Engine</h2>
        <p className="panel-subtitle">Identify information gaps and propose exploration targets</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_gaps ?? '-'}</span><span className="stat-label">Gaps</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.open_gaps ?? '-'}</span><span className="stat-label">Open</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_targets ?? '-'}</span><span className="stat-label">Targets</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_results ?? '-'}</span><span className="stat-label">Results</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.current_mode ?? '-'}</span><span className="stat-label">Mode</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'gap', 'explore'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Curiosity Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Gaps</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_gaps ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Open Gaps</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.open_gaps ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Targets</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_targets ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Results</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_results ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Current Mode</div>
                <div style={{ fontSize: 18, color: themeColors.primary }}>{stats.current_mode ?? '-'}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Info Gaps</h3>
            <button onClick={() => loadGaps()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {gaps.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No gaps recorded. Identify one in the Gap section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {gaps.slice(0, 10).map((g: any, i: number) => {
                  const id = g.gap_id ?? g.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{g.topic ?? 'untitled'}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{g.description ?? ''} · {id}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Gap Section */}
      {activeSection === 'gap' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Identify Information Gap</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Topic *</label>
                <input value={gapForm.topic} onChange={e => setGapForm({ ...gapForm, topic: e.target.value })} placeholder="e.g. cause_of_anomaly" />
              </div>
              <div className="form-group">
                <label>Gap Type</label>
                <select value={gapForm.gap_type} onChange={e => setGapForm({ ...gapForm, gap_type: e.target.value })}>
                  {INFO_GAP_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Urgency</label>
                <select value={gapForm.urgency} onChange={e => setGapForm({ ...gapForm, urgency: e.target.value })}>
                  {URGENCY_LEVELS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={gapForm.description} onChange={e => setGapForm({ ...gapForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleIdentifyGap} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Identify Gap</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Info Gaps ({gaps.length})</h3>
            <button onClick={() => loadGaps()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {gaps.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No gaps recorded. Identify one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {gaps.slice(0, 30).map((g: any, i: number) => {
                  const id = g.gap_id ?? g.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{g.topic ?? 'untitled'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{g.description ?? ''} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {g.gap_type && renderBadge(g.gap_type, themeColors.secondary)}
                          {g.urgency && renderBadge(g.urgency, urgencyColor(g.urgency))}
                          {g.status && renderBadge(g.status, statusColor(g.status))}
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => handleResolveGap(id)}>Resolve</button>
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

      {/* Explore Section */}
      {activeSection === 'explore' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Exploration Mode</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12, alignItems: 'end' }}>
              <div className="form-group">
                <label>Mode</label>
                <select value={currentMode} onChange={e => setCurrentMode(e.target.value)}>
                  {EXPLORATION_MODES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>
            <button onClick={handleSetMode} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Set Mode</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Propose Exploration Target</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Curiosity Type</label>
                <select value={targetForm.curiosity_type} onChange={e => setTargetForm({ ...targetForm, curiosity_type: e.target.value })}>
                  {CURIOSITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Novelty Metric</label>
                <select value={targetForm.novelty_metric} onChange={e => setTargetForm({ ...targetForm, novelty_metric: e.target.value })}>
                  {NOVELTY_METRICS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Expected Info Gain</label>
                <input value={targetForm.expected_info_gain} onChange={e => setTargetForm({ ...targetForm, expected_info_gain: e.target.value })} type="number" min="0" step="0.1" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description *</label>
                <input value={targetForm.description} onChange={e => setTargetForm({ ...targetForm, description: e.target.value })} placeholder="What to explore and why" />
              </div>
            </div>
            <button onClick={handleProposeTarget} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Propose Target</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Exploration Targets ({targets.length})</h3>
            <button onClick={() => loadTargets()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {targets.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No targets recorded. Propose one above.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {targets.slice(0, 30).map((t: any, i: number) => {
                  const id = t.target_id ?? t.id ?? i;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{t.description ?? 'untitled target'}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>info_gain: {t.expected_info_gain ?? '-'} · {id}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                          {t.curiosity_type && renderBadge(t.curiosity_type, themeColors.secondary)}
                          {t.novelty_metric && renderBadge(t.novelty_metric, '#6366f1')}
                          {t.status && renderBadge(t.status, statusColor(t.status))}
                          <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', marginLeft: 4 }} onClick={() => handleSelectTarget(id)}>Select</button>
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

export default CuriosityEnginePanel;
