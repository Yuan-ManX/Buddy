import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface VerifyResult {
  result_id: string;
  output_name: string;
  status: string;
  checks_passed: number;
  checks_total: number;
  score: number;
  issues: string[];
  verified_at: string;
}

interface VerificationStats {
  total_verifications: number;
  passed_verifications: number;
  failed_verifications: number;
  average_score: number;
  total_checks_run: number;
  profiles_count: number;
}

interface VerificationProfile {
  profile_id: string;
  name: string;
  description: string;
  rule_count: number;
  severity: string;
  enabled: boolean;
  created_at: string;
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

export const VerificationPipelinePanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<VerificationStats | null>(null);
  const [results, setResults] = useState<VerifyResult[]>([]);
  const [profiles, setProfiles] = useState<VerificationProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'verify' | 'results' | 'profiles'>('overview');

  // Verify form
  const [verifyForm, setVerifyForm] = useState({
    output_name: '',
    content: '',
    profile_id: '',
    strict_mode: false,
  });
  const [verifying, setVerifying] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, r, p] = await Promise.all([
        request<VerificationStats>('/verification-pipeline/stats').catch(() => null),
        request<VerifyResult[]>('/verification-pipeline/verify').catch(() => []),
        request<VerificationProfile[]>('/verification-pipeline/profiles').catch(() => []),
      ]);
      setStats(s);
      setResults(Array.isArray(r) ? r : (r as any)?.results || []);
      setProfiles(Array.isArray(p) ? p : (p as any)?.profiles || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load verification pipeline data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleVerify = async () => {
    if (!verifyForm.output_name.trim() || !verifyForm.content.trim()) return;
    try {
      setVerifying(true);
      const result = await request<any>('/verification-pipeline/verify', {
        method: 'POST',
        body: JSON.stringify({
          output_name: verifyForm.output_name,
          content: verifyForm.content,
          profile_id: verifyForm.profile_id || undefined,
          strict_mode: verifyForm.strict_mode,
        }),
      });
      toast.success(result.message || `Verification complete. Score: ${result.score || 'N/A'}`);
      setVerifyForm({ output_name: '', content: '', profile_id: '', strict_mode: false });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setVerifying(false);
    }
  };

  const statusColors: Record<string, string> = {
    passed: '#22c55e',
    failed: '#ef4444',
    partial: '#f59e0b',
    running: '#3b82f6',
    pending: '#9ca3af',
  };

  const scoreColor = (score: number): string => {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Verification Pipeline</h2>
          <p className="panel-subtitle">Verify outputs against quality standards and profiles</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading verification pipeline data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Verification Pipeline</h2>
        <p className="panel-subtitle">Automated verification, quality scoring, and validation profiles</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_verifications}</span>
              <span className="stat-label">Total Verifications</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.passed_verifications}</span>
              <span className="stat-label">Passed</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#ef4444' }}>{stats.failed_verifications}</span>
              <span className="stat-label">Failed</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: scoreColor(stats.average_score) }}>
                {(stats.average_score * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Avg Score</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.profiles_count}</span>
              <span className="stat-label">Profiles</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'verify', 'results', 'profiles'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Pipeline Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Verifications</span>
                <strong>{stats.total_verifications}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Passed</span>
                <strong style={{ color: '#22c55e' }}>{stats.passed_verifications}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Failed</span>
                <strong style={{ color: '#ef4444' }}>{stats.failed_verifications}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Average Score</span>
                <strong style={{ color: scoreColor(stats.average_score) }}>
                  {(stats.average_score * 100).toFixed(1)}%
                </strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Checks Run</span>
                <strong style={{ color: '#3b82f6' }}>{stats.total_checks_run}</strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Recent Results</h3>
              {results.length === 0 ? (
                <div className="panel-empty">No verification results yet</div>
              ) : (
                <div className="forge-skill-list">
                  {results.slice(0, 5).map(result => (
                    <div key={result.result_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{result.output_name}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[result.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {result.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Checks: {result.checks_passed}/{result.checks_total} passed</div>
                        <div>
                          Score:{' '}
                          <span style={{ color: scoreColor(result.score), fontWeight: 600 }}>
                            {(result.score * 100).toFixed(0)}%
                          </span>
                        </div>
                        {result.issues && result.issues.length > 0 && (
                          <div style={{ marginTop: 4 }}>
                            <strong>Issues:</strong>
                            <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                              {result.issues.slice(0, 3).map((issue, i) => (
                                <li key={i} style={{ fontSize: '0.85rem', color: '#ef4444' }}>{issue}</li>
                              ))}
                              {result.issues.length > 3 && (
                                <li style={{ fontSize: '0.85rem', color: '#9ca3af' }}>
                                  +{result.issues.length - 3} more
                                </li>
                              )}
                            </ul>
                          </div>
                        )}
                        <div>Verified: {new Date(result.verified_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Verify Section ── */}
      {activeSection === 'verify' && (
        <div className="dashboard-section">
          <h3>Verify Output</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Output Name</label>
              <input
                type="text"
                value={verifyForm.output_name}
                onChange={e => setVerifyForm(f => ({ ...f, output_name: e.target.value }))}
                placeholder="Name of the output to verify"
              />
            </div>
            <div className="form-group">
              <label>Content to Verify</label>
              <textarea
                rows={6}
                value={verifyForm.content}
                onChange={e => setVerifyForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the content to verify against quality standards..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Verification Profile</label>
                <select
                  value={verifyForm.profile_id}
                  onChange={e => setVerifyForm(f => ({ ...f, profile_id: e.target.value }))}
                >
                  <option value="">Default Profile</option>
                  {profiles.map(p => (
                    <option key={p.profile_id} value={p.profile_id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={verifyForm.strict_mode}
                    onChange={e => setVerifyForm(f => ({ ...f, strict_mode: e.target.checked }))}
                  />
                  Strict Mode
                </label>
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleVerify}
              disabled={verifying || !verifyForm.output_name.trim() || !verifyForm.content.trim()}
            >
              {verifying ? 'Verifying...' : 'Verify Output'}
            </button>
          </div>
        </div>
      )}

      {/* ── Results Section ── */}
      {activeSection === 'results' && (
        <div className="dashboard-section">
          <h3>Verification Results ({results.length})</h3>
          {results.length === 0 ? (
            <div className="panel-empty">No verification results yet. Go to the Verify tab to run one.</div>
          ) : (
            <div className="forge-skill-list">
              {results.map(result => (
                <div key={result.result_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{result.output_name}</div>
                    <span className="dashboard-badge" style={{
                      background: statusColors[result.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {result.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>
                      Checks: {result.checks_passed}/{result.checks_total} | Score:{' '}
                      <span style={{ color: scoreColor(result.score), fontWeight: 600 }}>
                        {(result.score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {result.issues && result.issues.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        <strong>Issues:</strong>
                        <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                          {result.issues.map((issue, i) => (
                            <li key={i} style={{ fontSize: '0.85rem', color: '#ef4444' }}>{issue}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div>Verified: {new Date(result.verified_at).toLocaleString()}</div>
                    <div>Result ID: {result.result_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Profiles Section ── */}
      {activeSection === 'profiles' && (
        <div className="dashboard-section">
          <h3>Verification Profiles ({profiles.length})</h3>
          {profiles.length === 0 ? (
            <div className="panel-empty">No verification profiles configured</div>
          ) : (
            <div className="forge-skill-list">
              {profiles.map(profile => (
                <div key={profile.profile_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{profile.name}</div>
                    <span className="dashboard-badge" style={{
                      background: profile.enabled ? '#22c55e' : '#9ca3af',
                      color: '#fff',
                    }}>
                      {profile.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{profile.description}</div>
                    <div>Rules: {profile.rule_count} | Severity: {profile.severity}</div>
                    <div>Created: {new Date(profile.created_at).toLocaleString()}</div>
                    <div>Profile ID: {profile.profile_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VerificationPipelinePanel;