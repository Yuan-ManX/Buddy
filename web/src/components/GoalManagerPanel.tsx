import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#4f46e5',
  secondary: '#818cf8',
  bg: '#eef2ff',
  border: '#c7d2fe',
  accent: '#e0e7ff',
  text: '#3730a3',
};

const GOAL_TYPES = ['outcome', 'process', 'learning', 'maintenance', 'avoidance', 'exploration'];
const GOAL_ORIGINS = ['user_request', 'self_generated', 'system_initiated', 'derived', 'calibrated'];
const PRIORITY_LEVELS = [0, 1, 2, 3, 4];

interface Goal {
  goal_id: string;
  id?: string;
  title: string;
  description?: string;
  goal_type?: string;
  origin?: string;
  priority?: number;
  status?: string;
  progress_score?: number;
  achievement_level?: string;
  deadline?: number | null;
  metrics?: Metric[];
  created_at?: number;
}

interface Metric {
  metric_id: string;
  id?: string;
  name: string;
  description?: string;
  target_value?: number;
  current_value?: number;
  unit?: string;
  threshold?: number;
}

export const GoalManagerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'track' | 'review'>('overview');

  // Create form
  const [createForm, setCreateForm] = useState({
    title: '',
    description: '',
    goal_type: 'outcome',
    origin: 'user_request',
    priority: '2',
  });
  const [goals, setGoals] = useState<Goal[]>([]);

  // Track state
  const [trackGoalId, setTrackGoalId] = useState('');
  const [trackGoal, setTrackGoal] = useState<Goal | null>(null);
  const [metricForm, setMetricForm] = useState({ name: '', target_value: '', unit: '' });
  const [metricUpdate, setMetricUpdate] = useState({ metricId: '', current_value: '' });

  // Review state
  const [reviewGoalId, setReviewGoalId] = useState('');
  const [reviewGoal, setReviewGoal] = useState<Goal | null>(null);
  const [reviewForm, setReviewForm] = useState({
    reviewer: '',
    achievement_assessment: '3',
    progress_notes: '',
    score: '',
  });
  const [prioritized, setPrioritized] = useState<Goal[]>([]);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.goalManager.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load goal manager data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadGoals = useCallback(async () => {
    try {
      const result = await api.goalManager.list();
      const list: Goal[] = Array.isArray(result) ? result : (result?.goals ?? []);
      setGoals(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load goals');
    }
  }, [toast]);

  useEffect(() => { loadStats(); }, [loadStats]);

  // Load data on section change
  useEffect(() => {
    if (activeSection === 'create') {
      loadGoals();
    } else if (activeSection === 'review') {
      loadGoals();
      api.goalManager.prioritize()
        .then((result: any) => {
          const list: Goal[] = Array.isArray(result) ? result : (result?.prioritized_goals ?? result?.goals ?? []);
          setPrioritized(list);
        })
        .catch((e: any) => toast.error(e.message || 'Failed to load prioritized goals'));
    }
  }, [activeSection, loadGoals, toast]);

  const handleCreateGoal = async () => {
    if (!createForm.title.trim()) return;
    try {
      await api.goalManager.create({
        title: createForm.title.trim(),
        description: createForm.description.trim() || undefined,
        goal_type: createForm.goal_type,
        origin: createForm.origin,
        priority: Number(createForm.priority),
      });
      toast.success(`Goal "${createForm.title}" created`);
      setCreateForm({ title: '', description: '', goal_type: 'outcome', origin: 'user_request', priority: '2' });
      loadGoals();
      loadStats();
    } catch (e: any) { toast.error(e.message || 'Failed to create goal'); }
  };

  const handleLoadTrackGoal = async () => {
    if (!trackGoalId.trim()) return;
    try {
      const goal = await api.goalManager.get(trackGoalId.trim());
      setTrackGoal(goal);
      toast.success('Goal loaded');
    } catch (e: any) { toast.error(e.message || 'Failed to load goal'); }
  };

  const handleAddMetric = async () => {
    if (!trackGoal || !metricForm.name.trim() || !trackGoal.goal_id) return;
    try {
      await api.goalManager.addMetric(trackGoal.goal_id, {
        name: metricForm.name.trim(),
        target_value: metricForm.target_value ? Number(metricForm.target_value) : undefined,
        unit: metricForm.unit.trim() || undefined,
      });
      toast.success(`Metric "${metricForm.name}" added`);
      setMetricForm({ name: '', target_value: '', unit: '' });
      const refreshed = await api.goalManager.get(trackGoal.goal_id);
      setTrackGoal(refreshed);
    } catch (e: any) { toast.error(e.message || 'Failed to add metric'); }
  };

  const handleUpdateMetric = async () => {
    if (!trackGoal || !trackGoal.goal_id || !metricUpdate.metricId.trim()) return;
    try {
      await api.goalManager.updateMetric(trackGoal.goal_id, metricUpdate.metricId.trim(), Number(metricUpdate.current_value) || 0);
      toast.success('Metric updated');
      setMetricUpdate({ metricId: '', current_value: '' });
      const refreshed = await api.goalManager.get(trackGoal.goal_id);
      setTrackGoal(refreshed);
    } catch (e: any) { toast.error(e.message || 'Failed to update metric'); }
  };

  const handleCheckAchievement = async () => {
    if (!trackGoal || !trackGoal.goal_id) return;
    try {
      const result = await api.goalManager.checkAchievement(trackGoal.goal_id);
      toast.success('Achievement checked');
      const refreshed = await api.goalManager.get(trackGoal.goal_id);
      setTrackGoal({ ...refreshed, ...result });
    } catch (e: any) { toast.error(e.message || 'Failed to check achievement'); }
  };

  const handleRecalculate = async () => {
    if (!trackGoal || !trackGoal.goal_id) return;
    try {
      const result = await api.goalManager.recalculate(trackGoal.goal_id);
      toast.success('Progress recalculated');
      const refreshed = await api.goalManager.get(trackGoal.goal_id);
      setTrackGoal({ ...refreshed, ...result });
    } catch (e: any) { toast.error(e.message || 'Failed to recalculate progress'); }
  };

  const handleLoadReviewGoal = async () => {
    if (!reviewGoalId.trim()) return;
    try {
      const goal = await api.goalManager.get(reviewGoalId.trim());
      setReviewGoal(goal);
      toast.success('Goal loaded for review');
    } catch (e: any) { toast.error(e.message || 'Failed to load goal'); }
  };

  const handleReview = async () => {
    if (!reviewGoal || !reviewGoal.goal_id) return;
    try {
      await api.goalManager.review(reviewGoal.goal_id, {
        reviewer: reviewForm.reviewer.trim() || undefined,
        achievement_assessment: Number(reviewForm.achievement_assessment),
        progress_notes: reviewForm.progress_notes.trim() || undefined,
        score: reviewForm.score ? Number(reviewForm.score) : undefined,
      });
      toast.success('Review submitted');
      setReviewForm({ reviewer: '', achievement_assessment: '3', progress_notes: '', score: '' });
      loadStats();
    } catch (e: any) { toast.error(e.message || 'Failed to submit review'); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🎯 Goal Manager</h2>
          <p className="panel-subtitle">Create, track, review, and prioritize agent goals</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading goal manager...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🎯 Goal Manager</h2>
        <p className="panel-subtitle">Create, track, review, and prioritize agent goals</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_goals ?? 0}</span><span className="stat-label">Total Goals</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.achievement_rate != null ? `${Math.round(stats.achievement_rate * 100)}%` : '-'}</span><span className="stat-label">Achievement</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.avg_progress != null ? `${Math.round(stats.avg_progress * 100)}%` : '-'}</span><span className="stat-label">Avg Progress</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.overdue_count ?? 0}</span><span className="stat-label">Overdue</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'track', 'review'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Goal Manager Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Goals</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_goals ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Achievement Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.achievement_rate != null ? `${Math.round(stats.achievement_rate * 100)}%` : '0%'}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Progress</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_progress != null ? `${Math.round(stats.avg_progress * 100)}%` : '0%'}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Overdue</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.overdue_count ?? 0}</div>
              </div>
            </div>

            {/* Breakdowns */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: 16 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>By Status</div>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem', color: themeColors.text, margin: 0 }}>{JSON.stringify(stats.goals_by_status ?? {}, null, 2)}</pre>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>By Priority</div>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem', color: themeColors.text, margin: 0 }}>{JSON.stringify(stats.goals_by_priority ?? {}, null, 2)}</pre>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>By Type</div>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem', color: themeColors.text, margin: 0 }}>{JSON.stringify(stats.goals_by_type ?? {}, null, 2)}</pre>
              </div>
            </div>
          </div>

          <OverdueAndBlocked themeColors={themeColors} />
        </div>
      )}

      {/* Create */}
      {activeSection === 'create' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Goal</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Title *</label>
              <input
                type="text"
                value={createForm.title}
                onChange={e => setCreateForm(f => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Improve response quality"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={createForm.description}
                onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the goal..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Goal Type</label>
                <select value={createForm.goal_type} onChange={e => setCreateForm(f => ({ ...f, goal_type: e.target.value }))}>
                  {GOAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Origin</label>
                <select value={createForm.origin} onChange={e => setCreateForm(f => ({ ...f, origin: e.target.value }))}>
                  {GOAL_ORIGINS.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Priority (0=critical)</label>
                <select value={createForm.priority} onChange={e => setCreateForm(f => ({ ...f, priority: e.target.value }))}>
                  {PRIORITY_LEVELS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateGoal}
              disabled={!createForm.title.trim()}
            >
              Create Goal
            </button>
          </div>

          <h4 style={{ color: themeColors.text, marginTop: 16 }}>Existing Goals</h4>
          <div style={{ display: 'grid', gap: 8 }}>
            {goals.length === 0 && (
              <div style={{ padding: 12, color: themeColors.text, background: themeColors.bg, borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                No goals yet.
              </div>
            )}
            {goals.map(g => (
              <div key={g.goal_id || g.id} style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>{g.title}</div>
                <div style={{ fontSize: '0.85rem', color: themeColors.text, opacity: 0.8 }}>
                  {g.goal_type && <span>type: {g.goal_type} · </span>}
                  {g.origin && <span>origin: {g.origin} · </span>}
                  <span>priority: {g.priority ?? '-'}</span>
                  {g.status && <span> · status: {g.status}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Track */}
      {activeSection === 'track' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Track Goal Progress</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Goal ID *</label>
                <input
                  type="text"
                  value={trackGoalId}
                  onChange={e => setTrackGoalId(e.target.value)}
                  placeholder="Goal ID"
                />
              </div>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary, alignSelf: 'flex-end' }}
                onClick={handleLoadTrackGoal}
                disabled={!trackGoalId.trim()}
              >
                Load Goal
              </button>
            </div>
          </div>

          {trackGoal && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h4 style={{ color: themeColors.text }}>{trackGoal.title}</h4>
              {trackGoal.description && <p style={{ color: themeColors.text, opacity: 0.85 }}>{trackGoal.description}</p>}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8, marginTop: 8 }}>
                <div style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontSize: '0.75rem', color: themeColors.text }}>Progress</div>
                  <div style={{ fontWeight: 700, color: themeColors.primary }}>{trackGoal.progress_score != null ? `${Math.round(trackGoal.progress_score * 100)}%` : '-'}</div>
                </div>
                <div style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontSize: '0.75rem', color: themeColors.text }}>Achievement</div>
                  <div style={{ fontWeight: 700, color: themeColors.primary }}>{trackGoal.achievement_level ?? '-'}</div>
                </div>
                <div style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                  <div style={{ fontSize: '0.75rem', color: themeColors.text }}>Status</div>
                  <div style={{ fontWeight: 700, color: themeColors.primary }}>{trackGoal.status ?? '-'}</div>
                </div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleCheckAchievement}>Check Achievement</button>
                <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleRecalculate}>Recalculate Progress</button>
              </div>

              {/* Metrics list */}
              <h5 style={{ color: themeColors.text, marginTop: 16 }}>Metrics</h5>
              {(trackGoal.metrics ?? []).length === 0 && <div style={{ fontSize: '0.85rem', color: themeColors.text }}>No metrics yet.</div>}
              {(trackGoal.metrics ?? []).map(m => (
                <div key={m.metric_id || m.id} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, marginBottom: 6, fontSize: '0.85rem', color: themeColors.text }}>
                  <strong>{m.name}</strong>: {m.current_value ?? 0} / {m.target_value ?? '-'} {m.unit ?? ''}
                </div>
              ))}
            </div>
          )}

          {/* Add metric */}
          {trackGoal && (
            <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
              <h4 style={{ color: themeColors.text }}>Add Metric</h4>
              <div className="form-row">
                <div className="form-group">
                  <label>Name *</label>
                  <input type="text" value={metricForm.name} onChange={e => setMetricForm(f => ({ ...f, name: e.target.value }))} placeholder="Metric name" />
                </div>
                <div className="form-group">
                  <label>Target Value</label>
                  <input type="number" value={metricForm.target_value} onChange={e => setMetricForm(f => ({ ...f, target_value: e.target.value }))} placeholder="e.g. 100" />
                </div>
                <div className="form-group">
                  <label>Unit</label>
                  <input type="text" value={metricForm.unit} onChange={e => setMetricForm(f => ({ ...f, unit: e.target.value }))} placeholder="e.g. ms" />
                </div>
              </div>
              <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleAddMetric} disabled={!metricForm.name.trim()}>Add Metric</button>

              <h4 style={{ color: themeColors.text, marginTop: 16 }}>Update Metric Value</h4>
              <div className="form-row">
                <div className="form-group">
                  <label>Metric ID *</label>
                  <input type="text" value={metricUpdate.metricId} onChange={e => setMetricUpdate(u => ({ ...u, metricId: e.target.value }))} placeholder="Metric ID" />
                </div>
                <div className="form-group">
                  <label>Current Value *</label>
                  <input type="number" value={metricUpdate.current_value} onChange={e => setMetricUpdate(u => ({ ...u, current_value: e.target.value }))} placeholder="e.g. 42" />
                </div>
              </div>
              <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleUpdateMetric} disabled={!metricUpdate.metricId.trim()}>Update Metric</button>
            </div>
          )}
        </div>
      )}

      {/* Review */}
      {activeSection === 'review' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Review Goal</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Goal ID *</label>
                <input
                  type="text"
                  value={reviewGoalId}
                  onChange={e => setReviewGoalId(e.target.value)}
                  placeholder="Goal ID"
                />
              </div>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary, alignSelf: 'flex-end' }}
                onClick={handleLoadReviewGoal}
                disabled={!reviewGoalId.trim()}
              >
                Load Goal
              </button>
            </div>
          </div>

          {reviewGoal && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h4 style={{ color: themeColors.text }}>{reviewGoal.title}</h4>
              {reviewGoal.description && <p style={{ color: themeColors.text, opacity: 0.85 }}>{reviewGoal.description}</p>}
              <div style={{ fontSize: '0.85rem', color: themeColors.text }}>
                progress: {reviewGoal.progress_score != null ? `${Math.round(reviewGoal.progress_score * 100)}%` : '-'} · achievement: {reviewGoal.achievement_level ?? '-'} · status: {reviewGoal.status ?? '-'}
              </div>
            </div>
          )}

          {reviewGoal && (
            <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
              <div className="form-group">
                <label>Reviewer</label>
                <input type="text" value={reviewForm.reviewer} onChange={e => setReviewForm(f => ({ ...f, reviewer: e.target.value }))} placeholder="Reviewer name" />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Achievement Assessment (0-5)</label>
                  <input type="number" min="0" max="5" step="1" value={reviewForm.achievement_assessment} onChange={e => setReviewForm(f => ({ ...f, achievement_assessment: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Score</label>
                  <input type="number" step="0.1" value={reviewForm.score} onChange={e => setReviewForm(f => ({ ...f, score: e.target.value }))} placeholder="Optional" />
                </div>
              </div>
              <div className="form-group">
                <label>Progress Notes</label>
                <textarea rows={3} value={reviewForm.progress_notes} onChange={e => setReviewForm(f => ({ ...f, progress_notes: e.target.value }))} placeholder="Notes on progress..." />
              </div>
              <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleReview}>Submit Review</button>
            </div>
          )}

          <h4 style={{ color: themeColors.text, marginTop: 16 }}>Prioritized Goals</h4>
          <div style={{ display: 'grid', gap: 8 }}>
            {prioritized.length === 0 && (
              <div style={{ padding: 12, color: themeColors.text, background: themeColors.bg, borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                No prioritized goals.
              </div>
            )}
            {prioritized.map(g => (
              <div key={g.goal_id || g.id} style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>{g.title}</div>
                <div style={{ fontSize: '0.85rem', color: themeColors.text, opacity: 0.8 }}>
                  priority: {g.priority ?? '-'} · status: {g.status ?? '-'} · progress: {g.progress_score != null ? `${Math.round(g.progress_score * 100)}%` : '-'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Helper sub-component for the overview section that loads overdue and blocked goals.
const OverdueAndBlocked: React.FC<{ themeColors: typeof themeColors }> = ({ themeColors }) => {
  const [overdue, setOverdue] = useState<Goal[]>([]);
  const [blocked, setBlocked] = useState<Goal[]>([]);

  useEffect(() => {
    api.goalManager.overdue()
      .then((r: any) => { const list: Goal[] = Array.isArray(r) ? r : (r?.goals ?? []); setOverdue(list); })
      .catch(() => setOverdue([]));
    api.goalManager.blocked()
      .then((r: any) => { const list: Goal[] = Array.isArray(r) ? r : (r?.goals ?? []); setBlocked(list); })
      .catch(() => setBlocked([]));
  }, []);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12 }}>
      <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
        <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>Overdue Goals</div>
        {overdue.length === 0 && <div style={{ fontSize: '0.85rem', color: themeColors.text }}>None</div>}
        {overdue.map(g => (
          <div key={g.goal_id || g.id} style={{ fontSize: '0.85rem', color: themeColors.text, padding: '4px 0', borderBottom: `1px solid ${themeColors.border}` }}>
            {g.title} {g.deadline ? `(due ${new Date(g.deadline).toLocaleDateString()})` : ''}
          </div>
        ))}
      </div>
      <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
        <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>Blocked Goals</div>
        {blocked.length === 0 && <div style={{ fontSize: '0.85rem', color: themeColors.text }}>None</div>}
        {blocked.map(g => (
          <div key={g.goal_id || g.id} style={{ fontSize: '0.85rem', color: themeColors.text, padding: '4px 0', borderBottom: `1px solid ${themeColors.border}` }}>
            {g.title} {g.status ? `· ${g.status}` : ''}
          </div>
        ))}
      </div>
    </div>
  );
};

export default GoalManagerPanel;
