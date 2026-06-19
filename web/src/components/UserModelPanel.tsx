import React, { useState, useEffect } from 'react';

interface UserProfile {
  user_id: string;
  interaction_count: number;
  total_sessions: number;
  first_interaction: string | null;
  last_interaction: string | null;
  dominant_dimensions: string[];
  profile_version: number;
  status?: string;
  traits_by_dimension: Record<string, { key: string; value: string; confidence: string; evidence: number; stability: number }[]>;
}

interface UserModelStats {
  total_profiles: number;
  total_observations: number;
  total_inferences: number;
  total_traits: number;
  avg_traits_per_user: number;
  users_by_activity: Record<string, number>;
}

export const UserModelPanel: React.FC = () => {
  const [stats, setStats] = useState<UserModelStats | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [userId, setUserId] = useState('default');
  const [loading, setLoading] = useState(false);
  const [inferenceResult, setInferenceResult] = useState<any>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/user-model/stats');
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error('Failed to fetch user model stats:', e);
    }
  };

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/user-model/profile/${userId}`);
      const data = await res.json();
      setProfile(data);
    } catch (e) {
      console.error('Failed to fetch profile:', e);
    }
    setLoading(false);
  };

  const runInference = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/user-model/infer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await res.json();
      setInferenceResult(data);
    } catch (e) {
      console.error('Failed to run inference:', e);
    }
    setLoading(false);
  };

  const runMaintenance = async () => {
    try {
      await fetch('/api/user-model/maintenance', { method: 'POST' });
      fetchStats();
    } catch (e) {
      console.error('Failed to run maintenance:', e);
    }
  };

  const confidenceColor = (level: string) => {
    switch (level) {
      case 'definitive': return '#22c55e';
      case 'established': return '#3b82f6';
      case 'confirmed': return '#8b5cf6';
      case 'emerging': return '#f59e0b';
      case 'speculative': return '#94a3b8';
      default: return '#94a3b8';
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>User Model Engine</h2>
        <span className="panel-subtitle">Cross-session user profiling</span>
      </div>

      <div className="panel-content">
        {/* Stats Overview */}
        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_profiles}</div>
              <div className="stat-label">Profiles</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_observations}</div>
              <div className="stat-label">Observations</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_inferences}</div>
              <div className="stat-label">Inferences</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_traits}</div>
              <div className="stat-label">Traits</div>
            </div>
          </div>
        )}

        {/* User Lookup */}
        <div className="section">
          <h3>User Lookup</h3>
          <div className="input-row">
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="User ID"
              className="text-input"
            />
            <button className="btn btn-primary" onClick={fetchProfile} disabled={loading}>
              Lookup
            </button>
            <button className="btn btn-secondary" onClick={runInference} disabled={loading}>
              Run Inference
            </button>
            <button className="btn btn-secondary" onClick={runMaintenance}>
              Maintenance
            </button>
          </div>
        </div>

        {/* Inference Result */}
        {inferenceResult && (
          <div className="section">
            <h3>Inference Result</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{inferenceResult.new_traits?.length || 0}</div>
                <div className="stat-label">New Traits</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{inferenceResult.updated_traits?.length || 0}</div>
                <div className="stat-label">Updated</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">v{inferenceResult.profile_version}</div>
                <div className="stat-label">Version</div>
              </div>
            </div>
          </div>
        )}

        {/* Profile Details */}
        {profile && profile.status !== 'no_profile' && (
          <div className="section">
            <h3>Profile: {profile.user_id}</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{profile.interaction_count}</div>
                <div className="stat-label">Interactions</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{profile.total_sessions}</div>
                <div className="stat-label">Sessions</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">v{profile.profile_version}</div>
                <div className="stat-label">Version</div>
              </div>
            </div>

            {profile.dominant_dimensions && (
              <div className="chip-row">
                {profile.dominant_dimensions.map((d: string) => (
                  <span key={d} className="chip">{d}</span>
                ))}
              </div>
            )}

            {Object.entries(profile.traits_by_dimension || {}).map(([dim, traits]) => (
              <div key={dim} className="section">
                <h4>{dim}</h4>
                <div className="trait-list">
                  {traits.map((trait: any, i: number) => (
                    <div key={i} className="trait-item">
                      <div className="trait-header">
                        <span className="trait-key">{trait.key}</span>
                        <span
                          className="trait-confidence"
                          style={{ color: confidenceColor(trait.confidence) }}
                        >
                          {trait.confidence}
                        </span>
                      </div>
                      <div className="trait-value">{typeof trait.value === 'string' ? trait.value : JSON.stringify(trait.value)}</div>
                      <div className="trait-meta">
                        <span>Evidence: {trait.evidence}</span>
                        <span>Stability: {(trait.stability * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};