import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface AutonomyPolicy {
  policy_id: string;
  name: string;
  description: string;
  risk_level: string;
  max_autonomy: string;
  requires_approval: boolean;
  constraints: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface ApprovalRequest {
  approval_id: string;
  action: string;
  requested_by: string;
  policy_id: string;
  risk_level: string;
  status: string;
  reason: string;
  requested_at: string;
  resolved_at: string | null;
}

interface AuditEntry {
  audit_id: string;
  action: string;
  agent_id: string;
  policy_id: string;
  result: string;
  details: string;
  timestamp: string;
}

interface TrustScore {
  agent_id: string;
  agent_name: string;
  trust_score: number;
  total_actions: number;
  approved_actions: number;
  denied_actions: number;
  last_evaluated: string;
}

interface Guardrail {
  guardrail_id: string;
  name: string;
  rule_type: string;
  condition: string;
  action: string;
  enabled: boolean;
  created_at: string;
}

interface AutonomyFrameworkStats {
  total_policies: number;
  active_policies: number;
  total_approvals: number;
  pending_approvals: number;
  total_audit_entries: number;
  average_trust_score: number;
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

export const AutonomyFrameworkPanel: React.FC = () => {
  const toast = useToast();

  const [stats, setStats] = useState<AutonomyFrameworkStats | null>(null);
  const [policies, setPolicies] = useState<AutonomyPolicy[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [trustScores, setTrustScores] = useState<TrustScore[]>([]);
  const [guardrails, setGuardrails] = useState<Guardrail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'policies' | 'authorize' | 'approvals' | 'audit' | 'trust'>('overview');

  // Create policy form
  const [policyForm, setPolicyForm] = useState({
    name: '',
    description: '',
    risk_level: 'low',
    max_autonomy: 'supervised',
    constraints: '',
  });
  const [creatingPolicy, setCreatingPolicy] = useState(false);

  // Authorize form
  const [authorizeForm, setAuthorizeForm] = useState({
    action: '',
    agent_id: '',
    policy_id: '',
    reason: '',
  });
  const [authorizing, setAuthorizing] = useState(false);
  const [authorizeResult, setAuthorizeResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, p, a, au, t, g] = await Promise.all([
        request<AutonomyFrameworkStats>('/autonomy/trust').catch(() => null),
        request<AutonomyPolicy[]>('/autonomy/policies').catch(() => []),
        request<ApprovalRequest[]>('/autonomy/approvals').catch(() => []),
        request<AuditEntry[]>('/autonomy/audit').catch(() => []),
        request<TrustScore[]>('/autonomy/trust').catch(() => []),
        request<Guardrail[]>('/autonomy/policies').catch(() => []),
      ]);
      setStats(s);
      setPolicies(Array.isArray(p) ? p : (p as any)?.policies || []);
      setApprovals(Array.isArray(a) ? a : (a as any)?.approvals || []);
      setAuditEntries(Array.isArray(au) ? au : (au as any)?.audit_entries || []);
      setTrustScores(Array.isArray(t) ? t : (t as any)?.trust_scores || []);
      setGuardrails(Array.isArray(g) ? g : (g as any)?.guardrails || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load autonomy framework data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreatePolicy = async () => {
    if (!policyForm.name.trim()) return;
    try {
      setCreatingPolicy(true);
      const result = await request<any>('/autonomy/policies', {
        method: 'POST',
        body: JSON.stringify({
          name: policyForm.name,
          description: policyForm.description || undefined,
          risk_level: policyForm.risk_level,
          max_autonomy: policyForm.max_autonomy,
          constraints: policyForm.constraints
            ? policyForm.constraints.split('\n').map(c => c.trim()).filter(Boolean)
            : undefined,
        }),
      });
      toast.success(result.message || 'Policy created successfully');
      setPolicyForm({ name: '', description: '', risk_level: 'low', max_autonomy: 'supervised', constraints: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setCreatingPolicy(false);
    }
  };

  const handleAuthorize = async () => {
    if (!authorizeForm.action.trim() || !authorizeForm.agent_id.trim()) return;
    try {
      setAuthorizing(true);
      setAuthorizeResult(null);
      const result = await request<any>('/autonomy/authorize', {
        method: 'POST',
        body: JSON.stringify({
          action: authorizeForm.action,
          agent_id: authorizeForm.agent_id,
          policy_id: authorizeForm.policy_id || undefined,
          reason: authorizeForm.reason || undefined,
        }),
      });
      setAuthorizeResult(result);
      toast.success(result.authorized ? 'Action authorized' : 'Action requires approval');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setAuthorizing(false);
    }
  };

  const handleApprove = async (approvalId: string) => {
    try {
      const result = await request<any>(`/autonomy/approvals/${approvalId}/approve`, {
        method: 'POST',
      });
      toast.success(result.message || 'Approval granted');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleDeny = async (approvalId: string) => {
    try {
      const result = await request<any>(`/autonomy/approvals/${approvalId}/deny`, {
        method: 'POST',
      });
      toast.success(result.message || 'Approval denied');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const riskLevelColors: Record<string, string> = {
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
    critical: '#dc2626',
  };

  const approvalStatusColors: Record<string, string> = {
    pending: '#f59e0b',
    approved: '#22c55e',
    denied: '#ef4444',
    auto_approved: '#3b82f6',
    expired: '#9ca3af',
  };

  const trustColor = (score: number): string => {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Autonomy Framework</h2>
          <p className="panel-subtitle">Manage agent autonomy policies, approvals, and trust</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading autonomy framework data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Autonomy Framework</h2>
        <p className="panel-subtitle">Define policies, authorize actions, and monitor agent autonomy with trust scores</p>
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
              <span className="stat-value">{stats.total_policies}</span>
              <span className="stat-label">Policies</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_policies}</span>
              <span className="stat-label">Active</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>{stats.pending_approvals}</span>
              <span className="stat-label">Pending</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#3b82f6' }}>{stats.total_audit_entries}</span>
              <span className="stat-label">Audit Entries</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: trustColor(stats.average_trust_score) }}>
                {(stats.average_trust_score * 100).toFixed(1)}%
              </span>
              <span className="stat-label">Avg Trust</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'policies', 'authorize', 'approvals', 'audit', 'trust'] as const).map(s => (
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
              <h3>Autonomy Overview</h3>
              <div className="dashboard-stat-row">
                <span>Total Policies</span>
                <strong>{stats.total_policies}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Active Policies</span>
                <strong style={{ color: '#22c55e' }}>{stats.active_policies}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Pending Approvals</span>
                <strong style={{ color: '#f59e0b' }}>{stats.pending_approvals}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Total Audit Entries</span>
                <strong style={{ color: '#3b82f6' }}>{stats.total_audit_entries}</strong>
              </div>
              <div className="dashboard-stat-row">
                <span>Average Trust Score</span>
                <strong style={{ color: trustColor(stats.average_trust_score) }}>
                  {(stats.average_trust_score * 100).toFixed(1)}%
                </strong>
              </div>

              <h3 style={{ marginTop: 24 }}>Guardrails</h3>
              {guardrails.length === 0 ? (
                <div className="panel-empty">No guardrails configured</div>
              ) : (
                <div className="forge-skill-list">
                  {guardrails.map(g => (
                    <div key={g.guardrail_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{g.name}</div>
                        <span className="dashboard-badge" style={{
                          background: g.enabled ? '#22c55e' : '#9ca3af',
                          color: '#fff',
                        }}>
                          {g.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Type: {g.rule_type} | Action: {g.action}</div>
                        <div>Condition: {g.condition}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <h3 style={{ marginTop: 24 }}>Trust Scores</h3>
              {trustScores.length === 0 ? (
                <div className="panel-empty">No trust scores computed yet</div>
              ) : (
                <div className="forge-skill-list">
                  {trustScores.slice(0, 5).map(ts => (
                    <div key={ts.agent_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{ts.agent_name}</div>
                        <span className="dashboard-badge" style={{
                          background: trustColor(ts.trust_score),
                          color: '#fff',
                        }}>
                          {Math.round(ts.trust_score * 100)}%
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Actions: {ts.total_actions} | Approved: {ts.approved_actions} | Denied: {ts.denied_actions}</div>
                        <div>Last Evaluated: {new Date(ts.last_evaluated).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Policies Section ── */}
      {activeSection === 'policies' && (
        <div className="dashboard-section">
          <h3>Create Policy</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Policy Name</label>
              <input
                type="text"
                value={policyForm.name}
                onChange={e => setPolicyForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Autonomy Policy"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={2}
                value={policyForm.description}
                onChange={e => setPolicyForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this policy governs"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Risk Level</label>
                <select
                  value={policyForm.risk_level}
                  onChange={e => setPolicyForm(f => ({ ...f, risk_level: e.target.value }))}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="form-group">
                <label>Max Autonomy</label>
                <select
                  value={policyForm.max_autonomy}
                  onChange={e => setPolicyForm(f => ({ ...f, max_autonomy: e.target.value }))}
                >
                  <option value="supervised">Supervised</option>
                  <option value="semi_autonomous">Semi-Autonomous</option>
                  <option value="autonomous">Autonomous</option>
                  <option value="full">Full</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Constraints (one per line)</label>
              <textarea
                rows={3}
                value={policyForm.constraints}
                onChange={e => setPolicyForm(f => ({ ...f, constraints: e.target.value }))}
                placeholder="Cannot modify production data\nCannot access sensitive APIs"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleCreatePolicy}
              disabled={creatingPolicy || !policyForm.name.trim()}
            >
              {creatingPolicy ? 'Creating...' : 'Create Policy'}
            </button>
          </div>

          <h3 style={{ marginTop: 24 }}>Existing Policies ({policies.length})</h3>
          {policies.length === 0 ? (
            <div className="panel-empty">No policies defined yet</div>
          ) : (
            <div className="forge-skill-list">
              {policies.map(policy => (
                <div key={policy.policy_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{policy.name}</div>
                    <span className="dashboard-badge" style={{
                      background: riskLevelColors[policy.risk_level] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {policy.risk_level}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{policy.description}</div>
                    <div>Max Autonomy: {policy.max_autonomy} | Requires Approval: {policy.requires_approval ? 'Yes' : 'No'}</div>
                    {policy.constraints && policy.constraints.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        <strong>Constraints:</strong>
                        <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                          {policy.constraints.map((c, i) => (
                            <li key={i} style={{ fontSize: '0.85rem', color: '#475569' }}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div style={{ marginTop: 4 }}>
                      <span className="dashboard-badge" style={{
                        background: policy.enabled ? '#22c55e' : '#9ca3af',
                        color: '#fff',
                        fontSize: '0.7rem',
                      }}>
                        {policy.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    <div>Created: {new Date(policy.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Authorize Section ── */}
      {activeSection === 'authorize' && (
        <div className="dashboard-section">
          <h3>Authorize Action</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Action</label>
              <input
                type="text"
                value={authorizeForm.action}
                onChange={e => setAuthorizeForm(f => ({ ...f, action: e.target.value }))}
                placeholder="e.g., delete_file, modify_config, deploy_service"
              />
            </div>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={authorizeForm.agent_id}
                onChange={e => setAuthorizeForm(f => ({ ...f, agent_id: e.target.value }))}
                placeholder="Enter agent ID..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Policy</label>
                <select
                  value={authorizeForm.policy_id}
                  onChange={e => setAuthorizeForm(f => ({ ...f, policy_id: e.target.value }))}
                >
                  <option value="">Default Policy</option>
                  {policies.map(p => (
                    <option key={p.policy_id} value={p.policy_id}>{p.name} ({p.risk_level})</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Reason</label>
              <textarea
                rows={2}
                value={authorizeForm.reason}
                onChange={e => setAuthorizeForm(f => ({ ...f, reason: e.target.value }))}
                placeholder="Why is this action needed?"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleAuthorize}
              disabled={authorizing || !authorizeForm.action.trim() || !authorizeForm.agent_id.trim()}
              style={{ background: '#8b5cf6' }}
            >
              {authorizing ? 'Authorizing...' : 'Authorize Action'}
            </button>
          </div>

          {authorizeResult && (
            <div style={{
              marginTop: 20,
              padding: 16,
              background: '#f8fafc',
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}>
              <h4>Authorization Result</h4>
              <div style={{ marginTop: 8, fontSize: '0.9rem', color: '#475569' }}>
                <div style={{ marginBottom: 4 }}>
                  <strong>Status:</strong>{' '}
                  <span className="dashboard-badge" style={{
                    background: authorizeResult.authorized ? '#22c55e' : '#f59e0b',
                    color: '#fff',
                  }}>
                    {authorizeResult.authorized ? 'Authorized' : 'Requires Approval'}
                  </span>
                </div>
                {authorizeResult.approval_id && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Approval ID:</strong> {authorizeResult.approval_id}
                  </div>
                )}
                {authorizeResult.reason && (
                  <div style={{ marginTop: 8, padding: 8, background: '#fff', borderRadius: 4, border: '1px solid #e2e8f0' }}>
                    <strong>Reason:</strong> {authorizeResult.reason}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Approvals Section ── */}
      {activeSection === 'approvals' && (
        <div className="dashboard-section">
          <h3>Approval Requests ({approvals.length})</h3>
          {approvals.length === 0 ? (
            <div className="panel-empty">No approval requests</div>
          ) : (
            <div className="forge-skill-list">
              {approvals.map(approval => (
                <div key={approval.approval_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{approval.action}</div>
                    <span className="dashboard-badge" style={{
                      background: approvalStatusColors[approval.status] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {approval.status}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Requested by: {approval.requested_by} | Risk: {approval.risk_level}</div>
                    <div>Reason: {approval.reason}</div>
                    <div>Requested: {new Date(approval.requested_at).toLocaleString()}</div>
                    {approval.resolved_at && (
                      <div>Resolved: {new Date(approval.resolved_at).toLocaleString()}</div>
                    )}
                    <div>Approval ID: {approval.approval_id}</div>
                  </div>
                  {approval.status === 'pending' && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                      <button
                        className="btn-sm"
                        style={{ background: '#22c55e', color: '#fff', border: 'none' }}
                        onClick={() => handleApprove(approval.approval_id)}
                      >
                        Approve
                      </button>
                      <button
                        className="btn-sm"
                        style={{ background: '#ef4444', color: '#fff', border: 'none' }}
                        onClick={() => handleDeny(approval.approval_id)}
                      >
                        Deny
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Audit Section ── */}
      {activeSection === 'audit' && (
        <div className="dashboard-section">
          <h3>Audit Trail ({auditEntries.length})</h3>
          {auditEntries.length === 0 ? (
            <div className="panel-empty">No audit entries recorded</div>
          ) : (
            <div className="forge-skill-list">
              {auditEntries.map(entry => (
                <div key={entry.audit_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{entry.action}</div>
                    <span className="dashboard-badge" style={{
                      background: entry.result === 'success' ? '#22c55e' : '#ef4444',
                      color: '#fff',
                    }}>
                      {entry.result}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Agent: {entry.agent_id} | Policy: {entry.policy_id}</div>
                    <div>{entry.details}</div>
                    <div>Timestamp: {new Date(entry.timestamp).toLocaleString()}</div>
                    <div>Audit ID: {entry.audit_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Trust Section ── */}
      {activeSection === 'trust' && (
        <div className="dashboard-section">
          <h3>Trust Scores ({trustScores.length})</h3>
          {trustScores.length === 0 ? (
            <div className="panel-empty">No trust scores computed yet</div>
          ) : (
            <div className="forge-skill-list">
              {trustScores.map(ts => (
                <div key={ts.agent_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{ts.agent_name}</div>
                    <span className="dashboard-badge" style={{
                      background: trustColor(ts.trust_score),
                      color: '#fff',
                    }}>
                      {Math.round(ts.trust_score * 100)}%
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Total Actions: {ts.total_actions}</div>
                    <div style={{ marginTop: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: '0.85rem', color: '#6b7280', minWidth: 80 }}>Trust</span>
                        <div style={{
                          flex: 1,
                          height: 8,
                          background: '#e5e7eb',
                          borderRadius: 4,
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${Math.min(ts.trust_score * 100, 100)}%`,
                            height: '100%',
                            background: trustColor(ts.trust_score),
                            borderRadius: 4,
                            transition: 'width 0.3s ease',
                          }} />
                        </div>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, minWidth: 40 }}>
                          {Math.round(ts.trust_score * 100)}%
                        </span>
                      </div>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      Approved: {ts.approved_actions} | Denied: {ts.denied_actions}
                    </div>
                    <div>Last Evaluated: {new Date(ts.last_evaluated).toLocaleString()}</div>
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

export default AutonomyFrameworkPanel;