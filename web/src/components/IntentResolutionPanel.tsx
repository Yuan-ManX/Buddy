import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface IntentResolutionStats {
  total_intents_resolved: number;
  average_confidence: number;
  average_ambiguity_score: number;
  top_categories: { category: string; count: number }[];
}

interface ResolveResult {
  primary_intent: string;
  confidence: number;
  sub_intents: string[];
  entities: { type: string; value: string; confidence: number }[];
  complexity: string;
  urgency: string;
  ambiguity_score: number;
  suggested_tools: string[];
  disambiguation_options: string[];
}

interface UserProfile {
  user_id: string;
  frequent_intents: { intent: string; count: number }[];
  patterns: string[];
  preferred_formats: string[];
}

interface ExtractedEntity {
  type: string;
  value: string;
  confidence: number;
}

// ── Request helper ──

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.error || body;
    } catch {}
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Component ──

export const IntentResolutionPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<IntentResolutionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'resolve' | 'profile' | 'entities'>('overview');

  // Resolve form
  const [resolveForm, setResolveForm] = useState({ prompt: '', context: '' });
  const [resolving, setResolving] = useState(false);
  const [resolveResult, setResolveResult] = useState<ResolveResult | null>(null);

  // Profile form
  const [profileUserId, setProfileUserId] = useState('');
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileResult, setProfileResult] = useState<UserProfile | null>(null);

  // Entities form
  const [entitiesPrompt, setEntitiesPrompt] = useState('');
  const [entitiesLoading, setEntitiesLoading] = useState(false);
  const [entitiesResult, setEntitiesResult] = useState<ExtractedEntity[] | null>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await request<IntentResolutionStats>('/intent-resolution/stats').catch(() => null);
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load intent resolution data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const handleResolve = async () => {
    if (!resolveForm.prompt.trim()) return;
    try {
      setResolving(true);
      const result = await request<ResolveResult>('/intent-resolution/resolve', {
        method: 'POST',
        body: JSON.stringify({
          prompt: resolveForm.prompt,
          context: resolveForm.context || undefined,
        }),
      });
      setResolveResult(result);
      toast.success('Intent resolved successfully');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setResolving(false);
    }
  };

  const handleProfileLookup = async () => {
    if (!profileUserId.trim()) return;
    try {
      setProfileLoading(true);
      const result = await request<UserProfile>(`/intent-resolution/profile/${encodeURIComponent(profileUserId.trim())}`);
      setProfileResult(result);
      toast.success('User profile loaded');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setProfileLoading(false);
    }
  };

  const handleExtractEntities = async () => {
    if (!entitiesPrompt.trim()) return;
    try {
      setEntitiesLoading(true);
      const result = await request<ExtractedEntity[]>('/intent-resolution/entities', {
        method: 'POST',
        body: JSON.stringify({ prompt: entitiesPrompt }),
      });
      setEntitiesResult(result);
      toast.success('Entities extracted');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setEntitiesLoading(false);
    }
  };

  const confidenceColor = (v: number) => {
    if (v >= 0.8) return '#22c55e';
    if (v >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Intent Resolution Engine</h2>
          <p className="panel-subtitle">Resolve, disambiguate, and enrich user intents</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading intent resolution data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Intent Resolution Engine</h2>
        <p className="panel-subtitle">Resolve, disambiguate, and enrich user intents</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_intents_resolved}</span>
              <span className="stat-label">Total Resolved</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: confidenceColor(stats.average_confidence) }}>
                {(stats.average_confidence * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Avg Confidence</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>
                {stats.average_ambiguity_score.toFixed(2)}
              </span>
              <span className="stat-label">Avg Ambiguity</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#06b6d4' }}>
                {stats.top_categories?.length || 0}
              </span>
              <span className="stat-label">Top Categories</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'resolve', 'profile', 'entities'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats ? (
            <>
              <h3>Resolution Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Intents Resolved</span>
                <strong>{stats.total_intents_resolved}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Average Confidence</span>
                <strong style={{ color: confidenceColor(stats.average_confidence) }}>
                  {(stats.average_confidence * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Average Ambiguity Score</span>
                <strong style={{ color: '#8b5cf6' }}>{stats.average_ambiguity_score.toFixed(2)}</strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Top Categories</h3>
              {stats.top_categories && stats.top_categories.length > 0 ? (
                <div className="forge-skill-list">
                  {stats.top_categories.map((cat, i) => (
                    <div key={i} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{cat.category}</div>
                        <span className="dashboard-badge" style={{ background: '#3b82f6', color: '#fff' }}>
                          {cat.count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="panel-empty">No category data available</div>
              )}
            </>
          ) : (
            <div className="panel-empty">No stats available. Try refreshing.</div>
          )}
        </div>
      )}

      {/* ── Resolve Tab ── */}
      {activeSection === 'resolve' && (
        <div className="dashboard-section">
          <h3>Resolve Intent</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Prompt</label>
              <textarea
                rows={4}
                value={resolveForm.prompt}
                onChange={e => setResolveForm(f => ({ ...f, prompt: e.target.value }))}
                placeholder="Enter the user prompt to resolve..."
              />
            </div>
            <div className="form-group">
              <label>Context (optional)</label>
              <textarea
                rows={2}
                value={resolveForm.context}
                onChange={e => setResolveForm(f => ({ ...f, context: e.target.value }))}
                placeholder="Additional context for disambiguation..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleResolve}
              disabled={resolving || !resolveForm.prompt.trim()}
            >
              {resolving ? 'Resolving...' : 'Resolve Intent'}
            </button>
          </div>

          {resolveResult && (
            <div className="forge-skill-list" style={{ marginTop: 16 }}>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">Primary Intent: {resolveResult.primary_intent}</div>
                  <span className="dashboard-badge" style={{
                    background: confidenceColor(resolveResult.confidence),
                    color: '#fff',
                  }}>
                    {resolveResult.confidence != null ? (resolveResult.confidence * 100).toFixed(1) + '%' : 'N/A'}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div>Complexity: {resolveResult.complexity || 'N/A'} | Urgency: {resolveResult.urgency || 'N/A'}</div>
                  <div>Ambiguity Score: {resolveResult.ambiguity_score != null ? resolveResult.ambiguity_score.toFixed(2) : 'N/A'}</div>
                </div>
              </div>

              {resolveResult.sub_intents && resolveResult.sub_intents.length > 0 && (
                <div className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Sub-Intents</div>
                  </div>
                  <div className="forge-skill-meta">
                    {resolveResult.sub_intents.map((si, i) => (
                      <div key={i}>• {si}</div>
                    ))}
                  </div>
                </div>
              )}

              {resolveResult.entities && resolveResult.entities.length > 0 && (
                <div className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Entities</div>
                  </div>
                  <div className="forge-skill-meta">
                    {resolveResult.entities.map((ent, i) => (
                      <div key={i}>{ent.type}: {ent.value} <span style={{ color: confidenceColor(ent.confidence), fontSize: '0.85em' }}>({(ent.confidence * 100).toFixed(0)}%)</span></div>
                    ))}
                  </div>
                </div>
              )}

              {resolveResult.suggested_tools && resolveResult.suggested_tools.length > 0 && (
                <div className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Suggested Tools</div>
                  </div>
                  <div className="forge-skill-meta">
                    {resolveResult.suggested_tools.map((t, i) => (
                      <div key={i}>• {t}</div>
                    ))}
                  </div>
                </div>
              )}

              {resolveResult.disambiguation_options && resolveResult.disambiguation_options.length > 0 && (
                <div className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Disambiguation Options</div>
                  </div>
                  <div className="forge-skill-meta">
                    {resolveResult.disambiguation_options.map((opt, i) => (
                      <div key={i}>• {opt}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Profile Tab ── */}
      {activeSection === 'profile' && (
        <div className="dashboard-section">
          <h3>User Intent Profile</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>User ID</label>
              <input
                type="text"
                value={profileUserId}
                onChange={e => setProfileUserId(e.target.value)}
                placeholder="Enter user ID..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleProfileLookup}
              disabled={profileLoading || !profileUserId.trim()}
            >
              {profileLoading ? 'Loading...' : 'Look Up Profile'}
            </button>
          </div>

          {profileResult && (
            <div className="forge-skill-list" style={{ marginTop: 16 }}>
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">User: {profileResult.user_id}</div>
                </div>
              </div>

              {profileResult.frequent_intents && profileResult.frequent_intents.length > 0 && (
                <div className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Frequent Intents</div>
                  </div>
                  <div className="forge-skill-meta">
                    {profileResult.frequent_intents.map((fi, i) => (
                      <div key={i}>
                        {fi.intent}
                        <span className="dashboard-badge" style={{ background: '#3b82f6', color: '#fff', marginLeft: 8, fontSize: '0.75em' }}>
                          {fi.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {profileResult.patterns && profileResult.patterns.length > 0 && (
                <div className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Patterns</div>
                  </div>
                  <div className="forge-skill-meta">
                    {profileResult.patterns.map((p, i) => (
                      <div key={i}>• {p}</div>
                    ))}
                  </div>
                </div>
              )}

              {profileResult.preferred_formats && profileResult.preferred_formats.length > 0 && (
                <div className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">Preferred Formats</div>
                  </div>
                  <div className="forge-skill-meta">
                    {profileResult.preferred_formats.map((pf, i) => (
                      <div key={i}>• {pf}</div>
                    ))}
                  </div>
                </div>
              )}

              {profileResult.frequent_intents.length === 0 &&
                profileResult.patterns.length === 0 &&
                profileResult.preferred_formats.length === 0 && (
                <div className="panel-empty">No profile data available for this user</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Entities Tab ── */}
      {activeSection === 'entities' && (
        <div className="dashboard-section">
          <h3>Extract Entities</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Prompt</label>
              <textarea
                rows={4}
                value={entitiesPrompt}
                onChange={e => setEntitiesPrompt(e.target.value)}
                placeholder="Enter a prompt to extract entities from..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleExtractEntities}
              disabled={entitiesLoading || !entitiesPrompt.trim()}
            >
              {entitiesLoading ? 'Extracting...' : 'Extract Entities'}
            </button>
          </div>

          {entitiesResult && (
            <div style={{ marginTop: 16 }}>
              {entitiesResult.length === 0 ? (
                <div className="panel-empty">No entities found in the prompt</div>
              ) : (
                <div className="forge-skill-list">
                  <div className="forge-skill-card">
                    <div className="forge-skill-header">
                      <div className="forge-skill-name">Extracted Entities ({entitiesResult.length})</div>
                    </div>
                    <div className="forge-skill-meta">
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border-color, #374151)' }}>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Type</th>
                            <th style={{ textAlign: 'left', padding: '6px 8px' }}>Value</th>
                            <th style={{ textAlign: 'right', padding: '6px 8px' }}>Confidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {entitiesResult.map((ent, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid var(--border-color, #374151)' }}>
                              <td style={{ padding: '6px 8px' }}>
                                <span className="dashboard-badge" style={{ background: '#3b82f6', color: '#fff', fontSize: '0.8em' }}>
                                  {ent.type}
                                </span>
                              </td>
                              <td style={{ padding: '6px 8px' }}>{ent.value}</td>
                              <td style={{ padding: '6px 8px', textAlign: 'right', color: confidenceColor(ent.confidence) }}>
                                {(ent.confidence * 100).toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default IntentResolutionPanel;