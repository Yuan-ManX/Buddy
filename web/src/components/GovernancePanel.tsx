import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { GovernanceStats, ApprovalRequest, PolicyRule, BudgetStatus, GovernanceEvaluation } from '../types';

export const GovernancePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<GovernanceStats | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'approvals' | 'policies' | 'budgets' | 'evaluate'>('overview');
  const [budgetAgentId, setBudgetAgentId] = useState('');
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [evalContext, setEvalContext] = useState('{}');
  const [evalResult, setEvalResult] = useState<GovernanceEvaluation | null>(null);
  const [showCreatePolicy, setShowCreatePolicy] = useState(false);
  const [policyForm, setPolicyForm] = useState({
    name: '', description: '', category: 'safety', level: 'server', action: 'ask',
    tool_patterns: '', file_patterns: '', max_cost_per_session: '',
    max_tokens_per_call: '', priority: '5',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, a] = await Promise.all([
        api.governance.stats(),
        api.governance.approvals(),
      ]);
      setStats(s);
      setApprovals(a.approvals);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load governance data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleApprove = async (requestId: string) => {
    try {
      await api.governance.approve(requestId);
      toast.success('Approval granted');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeny = async (requestId: string) => {
    try {
      await api.governance.deny(requestId);
      toast.success('Approval denied');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreatePolicy = async () => {
    if (!policyForm.name.trim()) return;
    try {
      await api.governance.createPolicy({
        name: policyForm.name,
        description: policyForm.description,
        category: policyForm.category,
        level: policyForm.level,
        action: policyForm.action,
        tool_patterns: policyForm.tool_patterns ? policyForm.tool_patterns.split(',').map(s => s.trim()) : undefined,
        file_patterns: policyForm.file_patterns ? policyForm.file_patterns.split(',').map(s => s.trim()) : undefined,
        max_cost_per_session: policyForm.max_cost_per_session ? parseFloat(policyForm.max_cost_per_session) : undefined,
        max_tokens_per_call: policyForm.max_tokens_per_call ? parseInt(policyForm.max_tokens_per_call) : undefined,
        priority: parseInt(policyForm.priority) || 5,
      });
      toast.success('Policy created');
      setShowCreatePolicy(false);
      setPolicyForm({ name: '', description: '', category: 'safety', level: 'server', action: 'ask', tool_patterns: '', file_patterns: '', max_cost_per_session: '', max_tokens_per_call: '', priority: '5' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleEvaluate = async () => {
    try {
      const ctx = JSON.parse(evalContext);
      const result = await api.governance.evaluate({ context: ctx });
      setEvalResult(result);
    } catch (e: any) {
      toast.error(e.message || 'Invalid JSON context');
    }
  };

  const handleLookupBudget = async () => {
    if (!budgetAgentId.trim()) return;
    try {
      const b = await api.governance.budget(budgetAgentId);
      setBudget(b);
    } catch (e: any) { toast.error(e.message); }
  };

  const actionColors: Record<string, string> = {
    allow: '#22c55e', block: '#ef4444', ask: '#f59e0b', log: '#3b82f6', throttle: '#8b5cf6',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Governance</h2>
          <p className="panel-subtitle">Policy-based agent control & approval management</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading governance data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Agent Governance</h2>
        <p className="panel-subtitle">Policy-based action control, approval flows & budget management</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_server_policies + stats.total_agent_policies + stats.total_session_policies}</span><span className="stat-label">Total Policies</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.pending_approvals}</span><span className="stat-label">Pending</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_approvals_processed}</span><span className="stat-label">Processed</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.active_budgets}</span><span className="stat-label">Active Budgets</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'approvals', 'policies', 'budgets', 'evaluate'] as const).map(s => (
          <button key={s} className={`forge-tab ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Policy Breakdown</h3>
          <div className="dashboard-stat-row"><span>Server-level Policies</span><strong>{stats.total_server_policies}</strong></div>
          <div className="dashboard-stat-row"><span>Agent-level Policies</span><strong>{stats.total_agent_policies}</strong></div>
          <div className="dashboard-stat-row"><span>Session-level Policies</span><strong>{stats.total_session_policies}</strong></div>
          <div className="dashboard-stat-row"><span>Pending Approvals</span><strong>{stats.pending_approvals}</strong></div>
          <div className="dashboard-stat-row"><span>Total Processed</span><strong>{stats.total_approvals_processed}</strong></div>

          <h3 style={{marginTop: 20}}>Budget Overview</h3>
          {Object.entries(stats.budgets).map(([aid, b]) => (
            <div key={aid} className="dashboard-stat-row" style={{flexDirection: 'column', alignItems: 'flex-start'}}>
              <span>{aid}</span>
              <div style={{width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 4, height: 8}}>
                <div style={{width: `${Math.min(100, (b.total_spent / b.budget_limit) * 100)}%`, background: b.budget_exceeded ? '#ef4444' : '#3b82f6', height: '100%', borderRadius: 4}} />
              </div>
              <span style={{fontSize: '0.75rem', color: '#6b7280'}}>${b.total_spent.toFixed(4)} / ${b.budget_limit.toFixed(2)}</span>
            </div>
          ))}

          <h3 style={{marginTop: 20}}>Recent Audit Log</h3>
          {stats.recent_audit.slice(0, 10).map((entry: any, i: number) => (
            <div key={i} className="dashboard-stat-row">
              <span>{entry.action}</span>
              <span style={{fontSize: '0.75rem', color: '#6b7280'}}>{new Date(entry.timestamp).toLocaleTimeString()}</span>
            </div>
          ))}
        </div>
      )}

      {/* Approvals */}
      {activeSection === 'approvals' && (
        <div className="dashboard-section">
          <h3>Pending Approvals ({approvals.length})</h3>
          {approvals.length === 0 ? (
            <div className="panel-empty">No pending approvals</div>
          ) : (
            <div className="forge-skill-list">
              {approvals.map(a => (
                <div key={a.request_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{a.action_description}</div>
                    <span className={`dashboard-badge ${a.status === 'pending' ? 'active' : 'inactive'}`}>{a.status}</span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Agent: {a.agent_id} | Rule: {a.rule_id}</div>
                    <div>Session: {a.session_id} | Created: {new Date(a.created_at).toLocaleString()}</div>
                  </div>
                  <div style={{display: 'flex', gap: 8, marginTop: 8}}>
                    <button className="btn-sm" style={{background: '#22c55e', color: '#fff', border: 'none'}} onClick={() => handleApprove(a.request_id)}>Approve</button>
                    <button className="btn-sm" style={{background: '#ef4444', color: '#fff', border: 'none'}} onClick={() => handleDeny(a.request_id)}>Deny</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Policies */}
      {activeSection === 'policies' && (
        <div className="dashboard-section">
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16}}>
            <h3>Policies</h3>
            <button className="btn-primary-sm" onClick={() => setShowCreatePolicy(!showCreatePolicy)}>
              {showCreatePolicy ? 'Cancel' : '+ New Policy'}
            </button>
          </div>

          {showCreatePolicy && (
            <div className="skill-execute" style={{marginBottom: 16, position: 'static'}}>
              <h3>Create Policy</h3>
              <div className="form-group"><label>Name</label><input type="text" value={policyForm.name} onChange={e => setPolicyForm(f => ({...f, name: e.target.value}))} placeholder="Policy name" /></div>
              <div className="form-group"><label>Description</label><input type="text" value={policyForm.description} onChange={e => setPolicyForm(f => ({...f, description: e.target.value}))} placeholder="What this policy does" /></div>
              <div className="form-row">
                <div className="form-group">
                  <label>Category</label>
                  <select value={policyForm.category} onChange={e => setPolicyForm(f => ({...f, category: e.target.value}))}>
                    {['safety', 'cost', 'security', 'privacy', 'quality', 'resource', 'custom'].map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Level</label>
                  <select value={policyForm.level} onChange={e => setPolicyForm(f => ({...f, level: e.target.value}))}>
                    {['server', 'agent', 'session'].map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Action</label>
                  <select value={policyForm.action} onChange={e => setPolicyForm(f => ({...f, action: e.target.value}))}>
                    {['allow', 'block', 'ask', 'log', 'throttle'].map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-group"><label>Tool Patterns (comma-separated)</label><input type="text" value={policyForm.tool_patterns} onChange={e => setPolicyForm(f => ({...f, tool_patterns: e.target.value}))} placeholder="write_file, execute_command" /></div>
              <div className="form-group"><label>File Patterns (comma-separated)</label><input type="text" value={policyForm.file_patterns} onChange={e => setPolicyForm(f => ({...f, file_patterns: e.target.value}))} placeholder="*.env, /etc/*" /></div>
              <div className="form-row">
                <div className="form-group"><label>Max Cost/Session</label><input type="text" value={policyForm.max_cost_per_session} onChange={e => setPolicyForm(f => ({...f, max_cost_per_session: e.target.value}))} placeholder="5.00" /></div>
                <div className="form-group"><label>Max Tokens/Call</label><input type="text" value={policyForm.max_tokens_per_call} onChange={e => setPolicyForm(f => ({...f, max_tokens_per_call: e.target.value}))} placeholder="100000" /></div>
                <div className="form-group"><label>Priority</label><input type="text" value={policyForm.priority} onChange={e => setPolicyForm(f => ({...f, priority: e.target.value}))} placeholder="5" /></div>
              </div>
              <button className="btn-primary" onClick={handleCreatePolicy}>Create Policy</button>
            </div>
          )}

          <div className="policy-list">
            {stats && Object.entries(stats.budgets).length === 0 && (
              <div className="panel-empty">No budgets configured yet</div>
            )}
            <div style={{marginTop: 16, color: '#6b7280', fontSize: '0.85rem'}}>
              Default policies are configured at server level. Create custom policies above.
            </div>
          </div>
        </div>
      )}

      {/* Budgets */}
      {activeSection === 'budgets' && (
        <div className="dashboard-section">
          <h3>Budget Lookup</h3>
          <div className="form-row">
            <div className="form-group" style={{flex: 1}}>
              <label>Agent ID</label>
              <input type="text" value={budgetAgentId} onChange={e => setBudgetAgentId(e.target.value)} placeholder="Enter agent ID" />
            </div>
            <div className="form-group" style={{alignSelf: 'flex-end'}}>
              <button className="btn-primary" onClick={handleLookupBudget}>Lookup</button>
            </div>
          </div>

          {budget && (
            <div className="forge-skill-card" style={{marginTop: 16}}>
              <div className="forge-skill-header"><div className="forge-skill-name">{budget.agent_id}</div><span className={`dashboard-badge ${budget.budget_exceeded ? 'inactive' : 'active'}`}>{budget.budget_exceeded ? 'EXCEEDED' : 'OK'}</span></div>
              <div className="forge-skill-meta">
                <div>Spent: <strong>${budget.total_spent.toFixed(4)}</strong> / ${budget.budget_limit.toFixed(2)}</div>
                <div>Remaining: <strong>${typeof budget.remaining === 'number' ? budget.remaining.toFixed(4) : '∞'}</strong></div>
                <div>Tokens: {budget.total_tokens} | Tool Calls: {budget.total_tool_calls}</div>
                <div>Warnings: {budget.warnings_issued}</div>
              </div>
              <div style={{width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 8, height: 10}}>
                <div style={{width: `${Math.min(100, (budget.total_spent / budget.budget_limit) * 100)}%`, background: budget.budget_exceeded ? '#ef4444' : '#3b82f6', height: '100%', borderRadius: 4}} />
              </div>
            </div>
          )}

          {stats && Object.keys(stats.budgets).length > 0 && (
            <div style={{marginTop: 20}}>
              <h3>All Budgets</h3>
              {Object.entries(stats.budgets).map(([aid, b]) => (
                <div key={aid} className="forge-skill-card" style={{marginBottom: 8}}>
                  <div className="forge-skill-header"><div className="forge-skill-name">{aid}</div><span className={`dashboard-badge ${b.budget_exceeded ? 'inactive' : 'active'}`}>{b.budget_exceeded ? 'EXCEEDED' : 'OK'}</span></div>
                  <div className="forge-skill-meta">
                    <div>${b.total_spent.toFixed(4)} / ${b.budget_limit.toFixed(2)} | Tokens: {b.total_tokens}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Evaluate */}
      {activeSection === 'evaluate' && (
        <div className="dashboard-section">
          <h3>Evaluate Context</h3>
          <div className="form-group">
            <label>Context (JSON)</label>
            <textarea
              rows={6}
              value={evalContext}
              onChange={e => setEvalContext(e.target.value)}
              placeholder='{"tool_name": "write_file", "file_path": "/etc/config", "tokens": 5000}'
              style={{fontFamily: 'monospace', fontSize: '0.85rem'}}
            />
          </div>
          <button className="btn-primary" onClick={handleEvaluate}>Evaluate</button>

          {evalResult && (
            <div className="forge-skill-card" style={{marginTop: 16}}>
              <div className="forge-skill-header">
                <div className="forge-skill-name">Result</div>
                <span className="dashboard-badge" style={{background: actionColors[evalResult.action] || '#666', color: '#fff'}}>{evalResult.action.toUpperCase()}</span>
              </div>
              <div className="forge-skill-meta">
                <div>Reason: {evalResult.reason}</div>
                {evalResult.triggered_rules && evalResult.triggered_rules.length > 0 && (
                  <div style={{marginTop: 8}}>
                    <strong>Triggered Rules:</strong>
                    {evalResult.triggered_rules.map((r: PolicyRule, i: number) => (
                      <div key={i} style={{marginLeft: 8, fontSize: '0.85rem'}}>
                        <span style={{color: actionColors[r.action]}}>{r.action}</span> — {r.name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GovernancePanel;