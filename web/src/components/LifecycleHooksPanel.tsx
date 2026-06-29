import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#0891b2',
  secondary: '#67e8f9',
  bg: '#ecfeff',
  border: '#a5f3fc',
  accent: '#cffafe',
  text: '#164e63',
};

const HOOK_EVENTS = [
  'session_start', 'session_end', 'user_prompt_submit', 'pre_tool_use', 'post_tool_use',
  'pre_model_call', 'post_model_call', 'agent_response', 'context_assembly', 'plan_created',
  'plan_step_start', 'plan_step_end', 'error_occurred', 'approval_requested', 'approval_resolved',
  'memory_write', 'memory_read', 'skill_invoked', 'delegation_requested', 'task_completed',
];
const HOOK_PHASES = ['pre', 'post', 'around'];
const HOOK_PRIORITIES = ['critical', 'high', 'normal', 'low', 'background'];

export const LifecycleHooksPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'register' | 'invoke' | 'log'>('overview');

  // Hook registration form
  const [hookForm, setHookForm] = useState({
    name: '',
    description: '',
    event: 'session_start',
    phase: 'pre',
    priority: 'normal',
    failure_policy: 'continue',
    owner: '',
  });

  // Invoke form
  const [invokeForm, setInvokeForm] = useState({
    event: 'session_start',
    phase: 'pre',
    session_id: '',
    agent_id: '',
    payload: '',
  });
  const [invokeResult, setInvokeResult] = useState<any>(null);

  // Hooks list and invocations
  const [hooks, setHooks] = useState<any[]>([]);
  const [invocations, setInvocations] = useState<any[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.lifecycleHooks.stats();
      setStats(s);
      const h = await api.lifecycleHooks.listHooks();
      setHooks(Array.isArray(h) ? h : (h?.hooks ?? []));
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load lifecycle hooks data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRegister = async () => {
    if (!hookForm.name.trim()) return;
    try {
      await api.lifecycleHooks.registerHook({ ...hookForm });
      toast.success(`Hook "${hookForm.name}" registered`);
      setHookForm({
        name: '',
        description: '',
        event: 'session_start',
        phase: 'pre',
        priority: 'normal',
        failure_policy: 'continue',
        owner: '',
      });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleInvoke = async () => {
    if (!invokeForm.event.trim()) return;
    let parsedPayload: any = undefined;
    if (invokeForm.payload.trim()) {
      try {
        parsedPayload = JSON.parse(invokeForm.payload);
      } catch (e: any) {
        toast.error('Invalid JSON payload');
        return;
      }
    }
    try {
      const result = await api.lifecycleHooks.invoke({
        ...invokeForm,
        payload: parsedPayload,
      });
      setInvokeResult(result);
      toast.success('Hooks invoked');
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const loadInvocations = useCallback(async () => {
    try {
      const result = await api.lifecycleHooks.invocations({ limit: 50 });
      setInvocations(Array.isArray(result) ? result : (result?.invocations ?? []));
    } catch (e: any) {
      toast.error(e.message);
    }
  }, [toast]);

  useEffect(() => {
    if (activeSection === 'log') {
      loadInvocations();
    }
  }, [activeSection, loadInvocations]);

  if (loading) {
    return (
      <div className="forge-panel">
        <div className="panel-header">
          <h2>🔗 Lifecycle Hooks</h2>
          <p className="panel-subtitle">Register, invoke, and audit agent lifecycle hooks</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading lifecycle hooks...</span></div>
      </div>
    );
  }

  return (
    <div
      className="forge-panel"
      style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}
    >
      <div className="panel-header">
        <h2>🔗 Lifecycle Hooks</h2>
        <p className="panel-subtitle">Register, invoke, and audit agent lifecycle hooks</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'register', 'invoke', 'log'] as const).map(s => (
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
      {activeSection === 'overview' && (
        <div className="forge-section">
          <div
            style={{
              padding: '20px',
              background: themeColors.bg,
              borderRadius: 8,
              border: `1px solid ${themeColors.border}`,
              marginBottom: 16,
            }}
          >
            <h3 style={{ color: themeColors.text }}>Lifecycle Hooks Overview</h3>
            <div className="forge-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="forge-card" style={{ padding: 12, background: '#fff', border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Hooks</div>
                <div className="forge-stat" style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {stats?.total_hooks ?? 0}
                </div>
              </div>
              <div className="forge-card" style={{ padding: 12, background: '#fff', border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Invocations</div>
                <div className="forge-stat" style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {stats?.total_invocations ?? 0}
                </div>
              </div>
              <div className="forge-card" style={{ padding: 12, background: '#fff', border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Chain Latency (ms)</div>
                <div className="forge-stat" style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {stats?.avg_chain_latency_ms ?? 0}
                </div>
              </div>
            </div>
          </div>

          <h3 style={{ color: themeColors.text }}>Registered Hooks</h3>
          <div style={{ overflowX: 'auto', border: `1px solid ${themeColors.border}`, borderRadius: 8 }}>
            <table className="forge-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: themeColors.accent }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Name</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Event</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Phase</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Priority</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Owner</th>
                </tr>
              </thead>
              <tbody>
                {hooks.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ padding: '12px', textAlign: 'center', color: themeColors.text }}>
                      No hooks registered yet.
                    </td>
                  </tr>
                )}
                {hooks.map((h, i) => (
                  <tr key={h?.hook_id ?? h?.id ?? i} style={{ borderTop: `1px solid ${themeColors.border}` }}>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{h?.name ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{h?.event ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{h?.phase ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{h?.priority ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{h?.owner ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Register */}
      {activeSection === 'register' && (
        <div className="forge-section">
          <h3 style={{ color: themeColors.text }}>Register Hook</h3>
          <div className="forge-form" style={{ marginBottom: 16 }}>
            <div className="form-row">
              <div className="form-group">
                <label>Name *</label>
                <input
                  className="forge-input"
                  type="text"
                  value={hookForm.name}
                  onChange={e => setHookForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. log-session-start"
                />
              </div>
              <div className="form-group">
                <label>Owner</label>
                <input
                  className="forge-input"
                  type="text"
                  value={hookForm.owner}
                  onChange={e => setHookForm(f => ({ ...f, owner: e.target.value }))}
                  placeholder="e.g. orchestrator"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <input
                className="forge-input"
                type="text"
                value={hookForm.description}
                onChange={e => setHookForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Short description of what this hook does"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Event</label>
                <select
                  className="forge-select"
                  value={hookForm.event}
                  onChange={e => setHookForm(f => ({ ...f, event: e.target.value }))}
                >
                  {HOOK_EVENTS.map(ev => (
                    <option key={ev} value={ev}>{ev}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Phase</label>
                <select
                  className="forge-select"
                  value={hookForm.phase}
                  onChange={e => setHookForm(f => ({ ...f, phase: e.target.value }))}
                >
                  {HOOK_PHASES.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Priority</label>
                <select
                  className="forge-select"
                  value={hookForm.priority}
                  onChange={e => setHookForm(f => ({ ...f, priority: e.target.value }))}
                >
                  {HOOK_PRIORITIES.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Failure Policy</label>
                <select
                  className="forge-select"
                  value={hookForm.failure_policy}
                  onChange={e => setHookForm(f => ({ ...f, failure_policy: e.target.value }))}
                >
                  <option value="continue">continue</option>
                  <option value="abort">abort</option>
                  <option value="retry">retry</option>
                  <option value="quarantine">quarantine</option>
                </select>
              </div>
            </div>
            <button
              className="forge-btn"
              style={{ background: themeColors.primary }}
              onClick={handleRegister}
              disabled={!hookForm.name.trim()}
            >
              Register Hook
            </button>
          </div>
        </div>
      )}

      {/* Invoke */}
      {activeSection === 'invoke' && (
        <div className="forge-section">
          <h3 style={{ color: themeColors.text }}>Invoke Hooks</h3>
          <div className="forge-form" style={{ marginBottom: 16 }}>
            <div className="form-row">
              <div className="form-group">
                <label>Event *</label>
                <select
                  className="forge-select"
                  value={invokeForm.event}
                  onChange={e => setInvokeForm(f => ({ ...f, event: e.target.value }))}
                >
                  {HOOK_EVENTS.map(ev => (
                    <option key={ev} value={ev}>{ev}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Phase</label>
                <select
                  className="forge-select"
                  value={invokeForm.phase}
                  onChange={e => setInvokeForm(f => ({ ...f, phase: e.target.value }))}
                >
                  {HOOK_PHASES.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID</label>
                <input
                  className="forge-input"
                  type="text"
                  value={invokeForm.session_id}
                  onChange={e => setInvokeForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Optional session ID"
                />
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input
                  className="forge-input"
                  type="text"
                  value={invokeForm.agent_id}
                  onChange={e => setInvokeForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="Optional agent ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Payload (JSON)</label>
              <textarea
                className="forge-input"
                rows={6}
                value={invokeForm.payload}
                onChange={e => setInvokeForm(f => ({ ...f, payload: e.target.value }))}
                placeholder='{"key": "value"}'
              />
            </div>
            <button
              className="forge-btn"
              style={{ background: themeColors.primary }}
              onClick={handleInvoke}
              disabled={!invokeForm.event.trim()}
            >
              Invoke Hooks
            </button>
          </div>

          {invokeResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Invocation Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>
                {JSON.stringify(invokeResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Log */}
      {activeSection === 'log' && (
        <div className="forge-section">
          <h3 style={{ color: themeColors.text }}>Invocation Log</h3>
          <div style={{ overflowX: 'auto', border: `1px solid ${themeColors.border}`, borderRadius: 8 }}>
            <table className="forge-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: themeColors.accent }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Invocation ID</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Hook ID</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Event</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Result</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Latency (ms)</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', color: themeColors.text }}>Error</th>
                </tr>
              </thead>
              <tbody>
                {invocations.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ padding: '12px', textAlign: 'center', color: themeColors.text }}>
                      No invocations recorded.
                    </td>
                  </tr>
                )}
                {invocations.map((inv, i) => (
                  <tr key={inv?.invocation_id ?? i} style={{ borderTop: `1px solid ${themeColors.border}` }}>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{inv?.invocation_id ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{inv?.hook_id ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{inv?.event ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{inv?.result ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{inv?.latency_ms ?? '-'}</td>
                    <td style={{ padding: '8px 12px', color: themeColors.text }}>{inv?.error ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default LifecycleHooksPanel;
