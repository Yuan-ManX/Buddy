import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#7c3aed',
  secondary: '#c4b5fd',
  bg: '#f5f3ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

const SYNC_FREQUENCIES = ['continuous', 'hourly', 'daily', 'weekly', 'on_demand'];
const DIMENSIONS = ['preferences', 'knowledge', 'behavior', 'decision_style', 'communication', 'values', 'goals', 'routines'];

interface AITwinStats {
  total_profiles: number;
  total_signals: number;
  total_interactions: number;
  active_twins: number;
}

export const AITwinPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<AITwinStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'profile' | 'learn' | 'predict' | 'mirror'>('overview');

  // Create profile form
  const [profileForm, setProfileForm] = useState({
    name: '', sync_frequency: 'daily',
  });

  // Learn form
  const [learnForm, setLearnForm] = useState({
    twin_id: '', dimension: 'preferences', action: '', context: '', outcome: '', weight: '',
  });

  // Predict form
  const [predictForm, setPredictForm] = useState({
    twin_id: '', dimension: 'preferences', context: '',
  });
  const [predictionResult, setPredictionResult] = useState<any>(null);

  // Mirror form
  const [mirrorForm, setMirrorForm] = useState({ twin_id: '', dimension: 'preferences' });
  const [mirrorResult, setMirrorResult] = useState<any>(null);

  // Get profile form
  const [profileId, setProfileId] = useState('');
  const [profileResult, setProfileResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.aiTwin.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load AI Twin data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateProfile = async () => {
    if (!profileForm.name.trim()) return;
    try {
      await api.aiTwin.createProfile({
        name: profileForm.name.trim(),
        sync_frequency: profileForm.sync_frequency,
      });
      toast.success(`Profile "${profileForm.name}" created`);
      setProfileForm({ name: '', sync_frequency: 'daily' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLearn = async () => {
    if (!learnForm.twin_id.trim() || !learnForm.action.trim()) return;
    try {
      await api.aiTwin.learn({
        twin_id: learnForm.twin_id.trim(),
        dimension: learnForm.dimension,
        action: learnForm.action.trim(),
        context: learnForm.context || undefined,
        outcome: learnForm.outcome || undefined,
        weight: learnForm.weight ? Number(learnForm.weight) : undefined,
      });
      toast.success('Learning signal recorded');
      setLearnForm({ twin_id: '', dimension: 'preferences', action: '', context: '', outcome: '', weight: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePredict = async () => {
    if (!predictForm.twin_id.trim() || !predictForm.context.trim()) return;
    try {
      const result = await api.aiTwin.predict({
        twin_id: predictForm.twin_id.trim(),
        dimension: predictForm.dimension,
        context: predictForm.context.trim(),
      });
      setPredictionResult(result);
      toast.success('Prediction generated');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetMirror = async () => {
    if (!mirrorForm.twin_id.trim()) return;
    try {
      const result = await api.aiTwin.mirror(mirrorForm.twin_id.trim(), mirrorForm.dimension);
      setMirrorResult(result);
      toast.success('Mirror data loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetProfile = async () => {
    if (!profileId.trim()) return;
    try {
      const result = await api.aiTwin.getProfile(profileId.trim());
      setProfileResult(result);
      toast.success('Profile loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🪞 AI Twin</h2>
          <p className="panel-subtitle">Personal digital identity with continuous mirroring and learning</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading AI Twin...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🪞 AI Twin</h2>
        <p className="panel-subtitle">Personal digital identity with continuous mirroring and learning</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_profiles}</span><span className="stat-label">Total Profiles</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_signals}</span><span className="stat-label">Total Signals</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_interactions}</span><span className="stat-label">Total Interactions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_twins}</span><span className="stat-label">Active Twins</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'profile', 'learn', 'predict', 'mirror'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>AI Twin Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Profiles</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_profiles}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Signals Collected</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_signals}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Interactions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_interactions}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Twins</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#22c55e' }}>{stats.active_twins}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Profile */}
      {activeSection === 'profile' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create AI Twin Profile</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={profileForm.name}
                onChange={e => setProfileForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g., My Digital Twin"
              />
            </div>
            <div className="form-group">
              <label>Sync Frequency</label>
              <select value={profileForm.sync_frequency} onChange={e => setProfileForm(f => ({ ...f, sync_frequency: e.target.value }))}>
                {SYNC_FREQUENCIES.map(f => (
                  <option key={f} value={f}>{f.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateProfile}
              disabled={!profileForm.name.trim()}
            >
              Create Profile
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Get Profile</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Twin ID *</label>
              <input
                type="text"
                value={profileId}
                onChange={e => setProfileId(e.target.value)}
                placeholder="Enter twin ID"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGetProfile}
              disabled={!profileId.trim()}
            >
              Get Profile
            </button>
          </div>

          {profileResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Profile Data</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(profileResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Learn */}
      {activeSection === 'learn' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Record Learning Signal</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Twin ID *</label>
              <input
                type="text"
                value={learnForm.twin_id}
                onChange={e => setLearnForm(f => ({ ...f, twin_id: e.target.value }))}
                placeholder="Enter twin ID"
              />
            </div>
            <div className="form-group">
              <label>Dimension</label>
              <select value={learnForm.dimension} onChange={e => setLearnForm(f => ({ ...f, dimension: e.target.value }))}>
                {DIMENSIONS.map(d => (
                  <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Action *</label>
              <input
                type="text"
                value={learnForm.action}
                onChange={e => setLearnForm(f => ({ ...f, action: e.target.value }))}
                placeholder="e.g., clicked_preference_A, chose_route_B"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Context</label>
                <input
                  type="text"
                  value={learnForm.context}
                  onChange={e => setLearnForm(f => ({ ...f, context: e.target.value }))}
                  placeholder="Context of the action"
                />
              </div>
              <div className="form-group">
                <label>Outcome</label>
                <input
                  type="text"
                  value={learnForm.outcome}
                  onChange={e => setLearnForm(f => ({ ...f, outcome: e.target.value }))}
                  placeholder="Result of the action"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Weight</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={learnForm.weight}
                onChange={e => setLearnForm(f => ({ ...f, weight: e.target.value }))}
                placeholder="0.0 - 1.0"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleLearn}
              disabled={!learnForm.twin_id.trim() || !learnForm.action.trim()}
            >
              Record Signal
            </button>
          </div>
        </div>
      )}

      {/* Predict */}
      {activeSection === 'predict' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Predict Behavior</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Twin ID *</label>
              <input
                type="text"
                value={predictForm.twin_id}
                onChange={e => setPredictForm(f => ({ ...f, twin_id: e.target.value }))}
                placeholder="Enter twin ID"
              />
            </div>
            <div className="form-group">
              <label>Dimension</label>
              <select value={predictForm.dimension} onChange={e => setPredictForm(f => ({ ...f, dimension: e.target.value }))}>
                {DIMENSIONS.map(d => (
                  <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Context *</label>
              <textarea
                rows={3}
                value={predictForm.context}
                onChange={e => setPredictForm(f => ({ ...f, context: e.target.value }))}
                placeholder="Describe the context for prediction..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handlePredict}
              disabled={!predictForm.twin_id.trim() || !predictForm.context.trim()}
            >
              Predict
            </button>
          </div>

          {predictionResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Prediction Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(predictionResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Mirror */}
      {activeSection === 'mirror' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Get Digital Mirror</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Twin ID *</label>
              <input
                type="text"
                value={mirrorForm.twin_id}
                onChange={e => setMirrorForm(f => ({ ...f, twin_id: e.target.value }))}
                placeholder="Enter twin ID"
              />
            </div>
            <div className="form-group">
              <label>Dimension</label>
              <select value={mirrorForm.dimension} onChange={e => setMirrorForm(f => ({ ...f, dimension: e.target.value }))}>
                {DIMENSIONS.map(d => (
                  <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGetMirror}
              disabled={!mirrorForm.twin_id.trim()}
            >
              Get Mirror
            </button>
          </div>

          {mirrorResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Mirror Data</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(mirrorResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AITwinPanel;