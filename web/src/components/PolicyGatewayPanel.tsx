import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#4f46e5',
  secondary: '#a5b4fc',
  bg: '#eef2ff',
  border: '#c7d2fe',
  accent: '#e0e7ff',
  text: '#312e81',
};

const RULE_LEVELS = ['global', 'agent', 'session'];
const RULE_ACTIONS = ['allow', 'block', 'approve', 'log'];

export const PolicyGatewayPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'rules' | 'evaluate' | 'approval'>('overview');

  // Rule form
  const [ruleForm, setRuleForm] = useState({
    name: '', description: '', level: 'global', category: '', action: 'allow', priority: '',
  });

  // Evaluate form
  const [evaluateForm, setEvaluateForm] = useState({
    agent_id: '', action_type: '', category: '',
  });

  // Approval form
  const [approvalForm, setApprovalForm] = useState({
    rule_id: '', agent_id: '', action_description: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.policyGateway.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load policy gateway data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAddRule = async () => {
    if (!ruleForm.name.trim()) return;
    try {
      await api.policyGateway.addRule({
        name: ruleForm.name.trim(),
        description: ruleForm.description || undefined,
        level: ruleForm.level,
        category: ruleForm.category || undefined,
        action: ruleForm.action,
        priority: ruleForm.priority ? Number(ruleForm.priority) : undefined,
      });
      toast.success(`Rule "${ruleForm.name}" added`);
      setRuleForm({ name: '', description: '', level: 'global', category: '', action: 'allow', priority: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleEvaluate = async () => {
    if (!evaluateForm.agent_id.trim() || !evaluateForm.action_type.trim()) return;
    try {
      await api.policyGateway.evaluate({
        agent_id: evaluateForm.agent_id.trim(),
        action_type: evaluateForm.action_type.trim(),
        category: evaluateForm.category || undefined,
      });
      toast.success('Policy evaluation completed');
      setEvaluateForm({ agent_id: '', action_type: '', category: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRequestApproval = async () => {
    if (!approvalForm.rule_id.trim() || !approvalForm.agent_id.trim() || !approvalForm.action_description.trim()) return;
    try {
      await api.policyGateway.requestApproval({
        rule_id: approvalForm.rule_id.trim(),
        agent_id: approvalForm.agent_id.trim(),
        action_description: approvalForm.action_description.trim(),
      });
      toast.success('Approval requested');
      setApprovalForm({ rule_id: '', agent_id: '', action_description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🛡️ Policy Gateway</h2>
          <p className="panel-subtitle">Enforce rules, evaluate actions, and manage approvals</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading policy gateway...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🛡️ Policy Gateway</h2>
        <p className="panel-subtitle">Enforce rules, evaluate actions, and manage approvals</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_rules ?? '-'}</span><span className="stat-label">Total Rules</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_rules ?? '-'}</span><span className="stat-label">Active Rules</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_evaluations ?? '-'}</span><span className="stat-label">Evaluations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.pending_approvals ?? '-'}</span><span className="stat-label">Pending Approvals</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'rules', 'evaluate', 'approval'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Policy Gateway Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Rules</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_rules ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Rules</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.active_rules ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Evaluations</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_evaluations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Pending Approvals</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.pending_approvals ?? 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rules */}
      {activeSection === 'rules' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Add Policy Rule</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={ruleForm.name}
                onChange={e => setRuleForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Rule name..."
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={ruleForm.description}
                onChange={e => setRuleForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this rule enforces..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Level</label>
                <select value={ruleForm.level} onChange={e => setRuleForm(f => ({ ...f, level: e.target.value }))}>
                  {RULE_LEVELS.map(l => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Category</label>
                <input
                  type="text"
                  value={ruleForm.category}
                  onChange={e => setRuleForm(f => ({ ...f, category: e.target.value }))}
                  placeholder="e.g. data_access, tool_use"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Action</label>
                <select value={ruleForm.action} onChange={e => setRuleForm(f => ({ ...f, action: e.target.value }))}>
                  {RULE_ACTIONS.map(a => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Priority</label>
                <input
                  type="number"
                  value={ruleForm.priority}
                  onChange={e => setRuleForm(f => ({ ...f, priority: e.target.value }))}
                  placeholder="Priority level"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddRule}
              disabled={!ruleForm.name.trim()}
            >
              Add Rule
            </button>
          </div>
        </div>
      )}

      {/* Evaluate */}
      {activeSection === 'evaluate' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Evaluate Action</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  type="text"
                  value={evaluateForm.agent_id}
                  onChange={e => setEvaluateForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="Agent ID"
                />
              </div>
              <div className="form-group">
                <label>Action Type *</label>
                <input
                  type="text"
                  value={evaluateForm.action_type}
                  onChange={e => setEvaluateForm(f => ({ ...f, action_type: e.target.value }))}
                  placeholder="e.g. run_tool, send_message"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Category</label>
              <input
                type="text"
                value={evaluateForm.category}
                onChange={e => setEvaluateForm(f => ({ ...f, category: e.target.value }))}
                placeholder="Optional category"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleEvaluate}
              disabled={!evaluateForm.agent_id.trim() || !evaluateForm.action_type.trim()}
            >
              Evaluate
            </button>
          </div>
        </div>
      )}

      {/* Approval */}
      {activeSection === 'approval' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Request Approval</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Rule ID *</label>
                <input
                  type="text"
                  value={approvalForm.rule_id}
                  onChange={e => setApprovalForm(f => ({ ...f, rule_id: e.target.value }))}
                  placeholder="Rule ID"
                />
              </div>
              <div className="form-group">
                <label>Agent ID *</label>
                <input
                  type="text"
                  value={approvalForm.agent_id}
                  onChange={e => setApprovalForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="Agent ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Action Description *</label>
              <textarea
                rows={3}
                value={approvalForm.action_description}
                onChange={e => setApprovalForm(f => ({ ...f, action_description: e.target.value }))}
                placeholder="Describe the action requiring approval..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRequestApproval}
              disabled={!approvalForm.rule_id.trim() || !approvalForm.agent_id.trim() || !approvalForm.action_description.trim()}
            >
              Request Approval
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PolicyGatewayPanel;
