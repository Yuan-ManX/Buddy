import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#d97706',
  bg: '#fffbeb',
  border: '#fde68a',
  text: '#92400e',
};

const ACTION_CATEGORIES = [
  'cognitive',
  'communicative',
  'tool_based',
  'navigational',
  'creative',
  'analytical',
  'system',
  'external_api',
];
const RISK_LEVELS = [0, 1, 2, 3, 4];
const EXECUTION_STATUSES = ['completed', 'failed', 'running', 'cancelled'];

// Format a success rate that may be either a 0-1 fraction or a 0-100 number.
const formatRate = (rate: any): string => {
  if (rate == null) return '-';
  const n = Number(rate);
  if (Number.isNaN(n)) return String(rate);
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(1)}%`;
};

export const ActionSpacePanel: React.FC = () => {
  const toast = useToast();
  const [activeSection, setActiveSection] = useState<'overview' | 'register' | 'feasibility' | 'executions'>('overview');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Register form + actions list
  const [registerForm, setRegisterForm] = useState({
    name: '',
    description: '',
    category: 'cognitive',
    risk_level: '0',
    estimated_duration_ms: '',
    estimated_cost: '',
  });
  const [actions, setActions] = useState<any[]>([]);

  // Feasibility form
  const [feasibilityActionId, setFeasibilityActionId] = useState('');
  const [feasibilityResult, setFeasibilityResult] = useState<any>(null);
  const [validationResult, setValidationResult] = useState<any>(null);

  // Executions form
  const [executionActionId, setExecutionActionId] = useState('');
  const [executionStatus, setExecutionStatus] = useState('completed');
  const [executionParameters, setExecutionParameters] = useState('{}');
  const [executionResultJson, setExecutionResultJson] = useState('{}');
  const [executions, setExecutions] = useState<any[]>([]);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.actionSpace.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load action space stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadActions = useCallback(async () => {
    try {
      setLoading(true);
      const result = await api.actionSpace.list();
      const list = Array.isArray(result) ? result : (result?.actions ?? []);
      setActions(list);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load actions');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadExecutions = useCallback(async () => {
    try {
      setLoading(true);
      const result = await api.actionSpace.listExecutions();
      const list = Array.isArray(result) ? result : (result?.executions ?? []);
      setExecutions(list);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load executions');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load data on section change
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
    } else if (activeSection === 'register') {
      loadActions();
    } else if (activeSection === 'feasibility') {
      loadActions();
    } else if (activeSection === 'executions') {
      loadActions();
      loadExecutions();
    }
  }, [activeSection, loadStats, loadActions, loadExecutions]);

  // Initial load
  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleRegister = async () => {
    if (!registerForm.name.trim()) return;
    try {
      setLoading(true);
      await api.actionSpace.register({
        name: registerForm.name.trim(),
        description: registerForm.description.trim() || undefined,
        category: registerForm.category,
        risk_level: Number(registerForm.risk_level),
        estimated_duration_ms: registerForm.estimated_duration_ms
          ? Number(registerForm.estimated_duration_ms)
          : undefined,
        estimated_cost: registerForm.estimated_cost
          ? Number(registerForm.estimated_cost)
          : undefined,
      });
      toast.success(`Action "${registerForm.name}" registered`);
      setRegisterForm({
        name: '',
        description: '',
        category: 'cognitive',
        risk_level: '0',
        estimated_duration_ms: '',
        estimated_cost: '',
      });
      loadActions();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckFeasibility = async () => {
    if (!feasibilityActionId) return;
    try {
      setLoading(true);
      const result = await api.actionSpace.checkFeasibility(feasibilityActionId, {
        parameters: {},
        context: {},
      });
      setFeasibilityResult(result);
      toast.success('Feasibility checked');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!feasibilityActionId) return;
    try {
      setLoading(true);
      const result = await api.actionSpace.validate(feasibilityActionId, {
        parameters: {},
      });
      setValidationResult(result);
      toast.success('Validation complete');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRecordExecution = async () => {
    if (!executionActionId) return;
    let parsedParameters: any = {};
    let parsedResult: any = {};
    try {
      parsedParameters = executionParameters.trim() ? JSON.parse(executionParameters) : {};
      parsedResult = executionResultJson.trim() ? JSON.parse(executionResultJson) : {};
    } catch (e: any) {
      toast.error('Invalid JSON in parameters or result');
      return;
    }
    try {
      setLoading(true);
      await api.actionSpace.recordExecution(executionActionId, {
        parameters: parsedParameters,
        status: executionStatus,
        result: parsedResult,
      });
      toast.success('Execution recorded');
      setExecutionParameters('{}');
      setExecutionResultJson('{}');
      loadExecutions();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !stats && activeSection === 'overview') {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🎯 Action Space</h2>
          <p className="panel-subtitle">Register actions, check feasibility, and record executions</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading action space...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="panel-container"
      style={{ '--accent-primary': themeColors.primary } as React.CSSProperties}
    >
      <div className="panel-header">
        <h2>🎯 Action Space</h2>
        <p className="panel-subtitle">Register actions, check feasibility, and record executions</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>
                {stats.total_actions ?? '-'}
              </span>
              <span className="stat-label">Actions</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>
                {stats.total_executions ?? '-'}
              </span>
              <span className="stat-label">Executions</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>
                {formatRate(stats.success_rate)}
              </span>
              <span className="stat-label">Success Rate</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: themeColors.primary }}>
                {stats.constraint_count ?? '-'}
              </span>
              <span className="stat-label">Constraints</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'register', 'feasibility', 'executions'] as const).map((s) => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={
              activeSection === s
                ? { background: themeColors.primary, borderColor: themeColors.primary }
                : {}
            }
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div
            style={{
              padding: '20px',
              background: themeColors.bg,
              borderRadius: 8,
              border: `1px solid ${themeColors.border}`,
              marginBottom: 16,
            }}
          >
            <h3 style={{ color: themeColors.text }}>Action Space Overview</h3>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                gap: 12,
                marginTop: 12,
              }}
            >
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Actions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {stats.total_actions ?? 0}
                </div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Executions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {stats.total_executions ?? 0}
                </div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Success Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {formatRate(stats.success_rate)}
                </div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Duration (ms)</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {stats.avg_duration_ms != null ? Number(stats.avg_duration_ms).toFixed(0) : 0}
                </div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Constraints</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {stats.constraint_count ?? 0}
                </div>
              </div>
            </div>

            {/* Breakdowns */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>By Category</div>
                {stats.actions_by_category && Object.keys(stats.actions_by_category).length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 18, color: themeColors.text, fontSize: '0.9rem' }}>
                    {Object.entries(stats.actions_by_category).map(([k, v]: any) => (
                      <li key={k}>
                        {k}: <strong>{v}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span style={{ color: themeColors.text, fontSize: '0.9rem' }}>No data</span>
                )}
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text, marginBottom: 6 }}>By Status</div>
                {stats.actions_by_status && Object.keys(stats.actions_by_status).length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 18, color: themeColors.text, fontSize: '0.9rem' }}>
                    {Object.entries(stats.actions_by_status).map(([k, v]: any) => (
                      <li key={k}>
                        {k}: <strong>{v}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span style={{ color: themeColors.text, fontSize: '0.9rem' }}>No data</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Register */}
      {activeSection === 'register' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Register Action</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={registerForm.name}
                  onChange={(e) => setRegisterForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. search_web"
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <select
                  value={registerForm.category}
                  onChange={(e) => setRegisterForm((f) => ({ ...f, category: e.target.value }))}
                >
                  {ACTION_CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={registerForm.description}
                onChange={(e) => setRegisterForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this action does..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Risk Level (0-4)</label>
                <select
                  value={registerForm.risk_level}
                  onChange={(e) => setRegisterForm((f) => ({ ...f, risk_level: e.target.value }))}
                >
                  {RISK_LEVELS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Estimated Duration (ms)</label>
                <input
                  type="number"
                  min="0"
                  value={registerForm.estimated_duration_ms}
                  onChange={(e) => setRegisterForm((f) => ({ ...f, estimated_duration_ms: e.target.value }))}
                  placeholder="e.g. 1500"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Estimated Cost ($)</label>
              <input
                type="number"
                min="0"
                step="0.0001"
                value={registerForm.estimated_cost}
                onChange={(e) => setRegisterForm((f) => ({ ...f, estimated_cost: e.target.value }))}
                placeholder="e.g. 0.01"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRegister}
              disabled={!registerForm.name.trim() || loading}
            >
              Register Action
            </button>
          </div>

          {/* Existing actions list */}
          <div
            style={{
              padding: '16px',
              background: themeColors.bg,
              borderRadius: 8,
              border: `1px solid ${themeColors.border}`,
            }}
          >
            <h4 style={{ color: themeColors.text }}>Existing Actions ({actions.length})</h4>
            {actions.length === 0 ? (
              <p style={{ color: themeColors.text, fontSize: '0.9rem' }}>No actions registered yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                {actions.map((a: any, i: number) => (
                  <div
                    key={a.id ?? a.name ?? i}
                    style={{
                      padding: '8px 10px',
                      background: '#fff',
                      borderRadius: 4,
                      border: `1px solid ${themeColors.border}`,
                      fontSize: '0.85rem',
                      color: themeColors.text,
                    }}
                  >
                    <strong>{a.name}</strong>
                    <span style={{ marginLeft: 8, opacity: 0.8 }}>
                      [{a.category ?? 'unknown'} · risk {a.risk_level ?? 0} · {a.status ?? 'active'}]
                    </span>
                    {a.description && (
                      <div style={{ marginTop: 2, opacity: 0.85 }}>{a.description}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Feasibility */}
      {activeSection === 'feasibility' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Check Feasibility</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Action *</label>
              <select
                value={feasibilityActionId}
                onChange={(e) => {
                  setFeasibilityActionId(e.target.value);
                  setFeasibilityResult(null);
                  setValidationResult(null);
                }}
              >
                <option value="">-- Select an action --</option>
                {actions.map((a: any, i: number) => (
                  <option key={a.id ?? i} value={a.id ?? a.name}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary }}
                onClick={handleCheckFeasibility}
                disabled={!feasibilityActionId || loading}
              >
                Check Feasibility
              </button>
              <button
                className="btn-primary"
                style={{ background: themeColors.primary, opacity: 0.85 }}
                onClick={handleValidate}
                disabled={!feasibilityActionId || loading}
              >
                Validate Parameters
              </button>
            </div>
          </div>

          {/* Feasibility report */}
          {feasibilityResult && (
            <div
              style={{
                padding: '16px',
                background: themeColors.bg,
                borderRadius: 8,
                border: `1px solid ${themeColors.border}`,
                marginBottom: 12,
              }}
            >
              <h4 style={{ color: themeColors.text }}>Feasibility Report</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
                <div style={{ color: themeColors.text, fontSize: '0.9rem' }}>
                  Level: <strong>{feasibilityResult.level ?? feasibilityResult.feasibility_level ?? '-'}</strong>
                </div>
                <div style={{ color: themeColors.text, fontSize: '0.9rem' }}>
                  Score: <strong>{feasibilityResult.score ?? feasibilityResult.feasibility_score ?? '-'}</strong>
                </div>
              </div>
              <FeasibilityList
                title="Satisfied Constraints"
                items={feasibilityResult.satisfied_constraints}
                textColor={themeColors.text}
              />
              <FeasibilityList
                title="Violated Constraints"
                items={feasibilityResult.violated_constraints}
                textColor={themeColors.text}
              />
              <FeasibilityList
                title="Warnings"
                items={feasibilityResult.warnings}
                textColor={themeColors.text}
              />
              <FeasibilityList
                title="Suggestions"
                items={feasibilityResult.suggestions}
                textColor={themeColors.text}
              />
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', color: themeColors.text, fontSize: '0.85rem' }}>
                  Raw report
                </summary>
                <pre
                  style={{
                    whiteSpace: 'pre-wrap',
                    fontSize: '0.8rem',
                    color: themeColors.text,
                    marginTop: 6,
                  }}
                >
                  {JSON.stringify(feasibilityResult, null, 2)}
                </pre>
              </details>
            </div>
          )}

          {/* Validation result */}
          {validationResult && (
            <div
              style={{
                padding: '16px',
                background: themeColors.bg,
                borderRadius: 8,
                border: `1px solid ${themeColors.border}`,
              }}
            >
              <h4 style={{ color: themeColors.text }}>Validation Result</h4>
              <pre
                style={{
                  whiteSpace: 'pre-wrap',
                  fontSize: '0.85rem',
                  color: themeColors.text,
                }}
              >
                {JSON.stringify(validationResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Executions */}
      {activeSection === 'executions' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Record Execution</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Action *</label>
                <select
                  value={executionActionId}
                  onChange={(e) => setExecutionActionId(e.target.value)}
                >
                  <option value="">-- Select an action --</option>
                  {actions.map((a: any, i: number) => (
                    <option key={a.id ?? i} value={a.id ?? a.name}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Status</label>
                <select
                  value={executionStatus}
                  onChange={(e) => setExecutionStatus(e.target.value)}
                >
                  {EXECUTION_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Parameters (JSON)</label>
              <textarea
                rows={3}
                value={executionParameters}
                onChange={(e) => setExecutionParameters(e.target.value)}
                placeholder="{}"
              />
            </div>
            <div className="form-group">
              <label>Result (JSON)</label>
              <textarea
                rows={3}
                value={executionResultJson}
                onChange={(e) => setExecutionResultJson(e.target.value)}
                placeholder="{}"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRecordExecution}
              disabled={!executionActionId || loading}
            >
              Record Execution
            </button>
          </div>

          {/* Recent executions */}
          <div
            style={{
              padding: '16px',
              background: themeColors.bg,
              borderRadius: 8,
              border: `1px solid ${themeColors.border}`,
            }}
          >
            <h4 style={{ color: themeColors.text }}>Recent Executions ({executions.length})</h4>
            {executions.length === 0 ? (
              <p style={{ color: themeColors.text, fontSize: '0.9rem' }}>No executions recorded yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                {executions.map((ex: any, i: number) => (
                  <div
                    key={ex.id ?? ex.execution_id ?? i}
                    style={{
                      padding: '8px 10px',
                      background: '#fff',
                      borderRadius: 4,
                      border: `1px solid ${themeColors.border}`,
                      fontSize: '0.85rem',
                      color: themeColors.text,
                    }}
                  >
                    <strong>{ex.action_id ?? ex.action_name ?? 'action'}</strong>
                    <span style={{ marginLeft: 8, opacity: 0.8 }}>
                      [{ex.status ?? 'unknown'}
                      {ex.duration_ms != null ? ` · ${ex.duration_ms}ms` : ''}]
                    </span>
                    {ex.error && (
                      <div style={{ marginTop: 2, color: '#b91c1c' }}>error: {ex.error}</div>
                    )}
                    {ex.result != null && (
                      <div style={{ marginTop: 2, opacity: 0.85 }}>
                        result: {typeof ex.result === 'string' ? ex.result : JSON.stringify(ex.result)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Helper component for rendering string array sections of the feasibility report.
const FeasibilityList: React.FC<{ title: string; items: any; textColor: string }> = ({
  title,
  items,
  textColor,
}) => {
  const list = Array.isArray(items)
    ? items
    : items
      ? [items]
      : [];
  if (list.length === 0) return null;
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontWeight: 600, color: textColor, fontSize: '0.85rem' }}>{title}</div>
      <ul style={{ margin: '4px 0 0 0', paddingLeft: 18, color: textColor, fontSize: '0.85rem' }}>
        {list.map((item: any, idx: number) => (
          <li key={idx}>
            {typeof item === 'string' ? item : JSON.stringify(item)}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ActionSpacePanel;
