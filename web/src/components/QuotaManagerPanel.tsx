import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: orange/amber for quota & rate limiting
const themeColors = {
  primary: '#f59e0b',
  secondary: '#fbbf24',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

// Enum values must match backend QuotaType / RetryStrategy exactly (UPPERCASE).
const QUOTA_TYPES = ['REQUEST_COUNT', 'TOKEN_COUNT', 'COST_USD', 'CONCURRENT', 'CUSTOM'];
const RETRY_STRATEGIES = ['NONE', 'FIXED', 'LINEAR', 'EXPONENTIAL', 'EXPONENTIAL_JITTER'];

export const QuotaManagerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'limit' | 'consume' | 'retry'>('overview');

  // Limits list
  const [limits, setLimits] = useState<any[]>([]);
  const [backpressure, setBackpressure] = useState<string>('');

  // Usage / window
  const [usage, setUsage] = useState<any>(null);
  const [window, setWindow] = useState<any>(null);

  // Limit form
  const [limitForm, setLimitForm] = useState({
    resource: '',
    quota_type: 'REQUEST_COUNT',
    max_value: '100',
    window_seconds: '60',
    description: '',
  });

  // Consume form
  const [consumeForm, setConsumeForm] = useState({
    resource: '',
    quota_type: 'REQUEST_COUNT',
    amount: '1',
  });
  const [consumeResult, setConsumeResult] = useState<any>(null);

  // Retry policy form
  const [retryForm, setRetryForm] = useState({
    name: '',
    max_retries: '3',
    base_delay_ms: '100',
    max_delay_ms: '10000',
    strategy: 'EXPONENTIAL_JITTER',
    retryable_status_codes: '429,500,502,503',
  });
  const [retryPolicies, setRetryPolicies] = useState<any[]>([]);

  // Compute retry delay form
  const [delayForm, setDelayForm] = useState({
    policy_id: '',
    attempt_number: '1',
    last_status_code: '429',
  });
  const [delayResult, setDelayResult] = useState<any>(null);

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.quotaManager.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load quota manager stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadLimits = useCallback(async () => {
    try {
      const result = await api.quotaManager.listLimits();
      const list = Array.isArray(result) ? result : (result?.limits ?? []);
      setLimits(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load limits');
    }
  }, [toast]);

  const loadBackpressure = useCallback(async () => {
    try {
      const result = await api.quotaManager.backpressure();
      setBackpressure(result?.backpressure_level ?? '-');
    } catch (e: any) {
      // Silent fail; not critical
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + limits when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadLimits();
      loadBackpressure();
    }
  }, [activeSection, loadStats, loadLimits, loadBackpressure]);

  const handleRegisterLimit = async () => {
    if (!limitForm.resource.trim()) {
      toast.error('Resource name is required');
      return;
    }
    try {
      const codes = limitForm.retryable_status_codes
        .split(',')
        .map(s => parseInt(s.trim(), 10))
        .filter(n => !isNaN(n));
      await api.quotaManager.registerLimit({
        resource: limitForm.resource.trim(),
        quota_type: limitForm.quota_type,
        max_value: Number(limitForm.max_value),
        window_seconds: Number(limitForm.window_seconds),
        description: limitForm.description.trim() || undefined,
      });
      void codes;
      toast.success('Quota limit registered');
      setLimitForm({ resource: '', quota_type: 'REQUEST_COUNT', max_value: '100', window_seconds: '60', description: '' });
      await loadLimits();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeleteLimit = async (limitId: string) => {
    try {
      await api.quotaManager.unregisterLimit(limitId);
      toast.success('Limit removed');
      loadLimits();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCheck = async () => {
    if (!consumeForm.resource.trim()) return;
    try {
      const result = await api.quotaManager.check({
        resource: consumeForm.resource.trim(),
        quota_type: consumeForm.quota_type,
        amount: Number(consumeForm.amount),
      });
      toast.success(result?.allowed ? 'Allowed' : 'Would exceed quota');
      setConsumeResult(result);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleConsume = async () => {
    if (!consumeForm.resource.trim()) return;
    try {
      const result = await api.quotaManager.consume({
        resource: consumeForm.resource.trim(),
        quota_type: consumeForm.quota_type,
        amount: Number(consumeForm.amount),
      });
      toast.success('Quota consumed');
      setConsumeResult(result);
      // Refresh usage if same resource
      if (consumeForm.resource.trim()) {
        const u = await api.quotaManager.getUsage(consumeForm.resource.trim(), consumeForm.quota_type).catch(() => null);
        setUsage(u);
      }
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRelease = async () => {
    if (!consumeForm.resource.trim()) return;
    try {
      const result = await api.quotaManager.release({
        resource: consumeForm.resource.trim(),
        quota_type: consumeForm.quota_type,
        amount: Number(consumeForm.amount),
      });
      toast.success(result?.released ? 'Quota released' : 'Release failed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFetchUsage = async () => {
    if (!consumeForm.resource.trim()) return;
    try {
      const u = await api.quotaManager.getUsage(consumeForm.resource.trim(), consumeForm.quota_type);
      setUsage(u);
      const w = await api.quotaManager.getWindow(consumeForm.resource.trim()).catch(() => null);
      setWindow(w);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRegisterRetry = async () => {
    if (!retryForm.name.trim()) {
      toast.error('Policy name required');
      return;
    }
    try {
      const codes = retryForm.retryable_status_codes
        .split(',')
        .map(s => parseInt(s.trim(), 10))
        .filter(n => !isNaN(n));
      const result = await api.quotaManager.registerRetryPolicy({
        name: retryForm.name.trim(),
        max_retries: Number(retryForm.max_retries),
        base_delay_ms: Number(retryForm.base_delay_ms),
        max_delay_ms: Number(retryForm.max_delay_ms),
        strategy: retryForm.strategy,
        retryable_status_codes: codes,
      });
      toast.success('Retry policy registered');
      setRetryPolicies(prev => [...prev.filter(p => (p.policy_id ?? p.id) !== (result?.policy_id ?? result?.id)), result]);
      setRetryForm({ name: '', max_retries: '3', base_delay_ms: '100', max_delay_ms: '10000', strategy: 'EXPONENTIAL_JITTER', retryable_status_codes: '429,500,502,503' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleComputeDelay = async () => {
    if (!delayForm.policy_id.trim()) {
      toast.error('Policy ID required');
      return;
    }
    try {
      const result = await api.quotaManager.computeRetryDelay({
        policy_id: delayForm.policy_id.trim(),
        attempt_number: Number(delayForm.attempt_number),
        last_status_code: delayForm.last_status_code.trim() ? Number(delayForm.last_status_code) : null,
      });
      setDelayResult(result);
      toast.success(`Delay: ${result?.delay_ms ?? '-'} ms (will retry: ${result?.will_retry ?? false})`);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🚦 Quota Manager</h2>
          <p className="panel-subtitle">Rate limiting, backpressure, and retry orchestration</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading quota manager...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🚦 Quota Manager</h2>
        <p className="panel-subtitle">Rate limiting, backpressure, and retry orchestration</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_limits ?? '-'}</span><span className="stat-label">Limits</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_windows ?? '-'}</span><span className="stat-label">Windows</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_consumed ?? '-'}</span><span className="stat-label">Consumed</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.rejected_requests ?? '-'}</span><span className="stat-label">Rejected</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{backpressure || stats.backpressure_level || '-'}</span><span className="stat-label">Backpressure</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'limit', 'consume', 'retry'] as const).map(s => (
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

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Quota Manager Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Limits</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_limits ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Windows</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_windows ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Consumed</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_consumed ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Rejected Requests</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.rejected_requests ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Retry Policies</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_retry_policies ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Backpressure Level</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{backpressure || stats.backpressure_level || 'none'}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Configured Limits</h3>
            <button onClick={loadLimits} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {limits.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No quota limits registered. Create one in the Limit section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {limits.map((l: any) => {
                  const id = l.limit_id ?? l.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{l.resource}</div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{l.quota_type} · max {l.max_value} / {l.window_seconds}s · {id}</div>
                      </div>
                      <button className="btn-sm" style={{ background: '#ef4444', color: '#fff' }} onClick={() => handleDeleteLimit(id)}>Delete</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Limit Section */}
      {activeSection === 'limit' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Quota Limit</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Resource *</label>
                <input value={limitForm.resource} onChange={e => setLimitForm({ ...limitForm, resource: e.target.value })} placeholder="e.g. llm.gpt-4" />
              </div>
              <div className="form-group">
                <label>Quota Type</label>
                <select value={limitForm.quota_type} onChange={e => setLimitForm({ ...limitForm, quota_type: e.target.value })}>
                  {QUOTA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Max Value</label>
                <input value={limitForm.max_value} onChange={e => setLimitForm({ ...limitForm, max_value: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Window (seconds)</label>
                <input value={limitForm.window_seconds} onChange={e => setLimitForm({ ...limitForm, window_seconds: e.target.value })} type="number" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={limitForm.description} onChange={e => setLimitForm({ ...limitForm, description: e.target.value })} placeholder="optional notes" />
              </div>
            </div>
            <button onClick={handleRegisterLimit} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Limit</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Existing Limits</h3>
            <button onClick={loadLimits} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {limits.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No limits yet.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {limits.map((l: any) => {
                  const id = l.limit_id ?? l.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{l.resource}</div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{l.quota_type} · max {l.max_value} / {l.window_seconds}s</div>
                      </div>
                      <button className="btn-sm" style={{ background: '#ef4444', color: '#fff' }} onClick={() => handleDeleteLimit(id)}>Delete</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Consume Section */}
      {activeSection === 'consume' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Check / Consume / Release Quota</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Resource *</label>
                <input value={consumeForm.resource} onChange={e => setConsumeForm({ ...consumeForm, resource: e.target.value })} placeholder="e.g. llm.gpt-4" />
              </div>
              <div className="form-group">
                <label>Quota Type</label>
                <select value={consumeForm.quota_type} onChange={e => setConsumeForm({ ...consumeForm, quota_type: e.target.value })}>
                  {QUOTA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Amount</label>
                <input value={consumeForm.amount} onChange={e => setConsumeForm({ ...consumeForm, amount: e.target.value })} type="number" />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <button onClick={handleCheck} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Check</button>
              <button onClick={handleConsume} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Consume</button>
              <button onClick={handleRelease} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Release</button>
              <button onClick={handleFetchUsage} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Fetch Usage</button>
            </div>
          </div>

          {consumeResult && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Last Result</h3>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(consumeResult, null, 2)}</pre>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {usage && (
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <h3 style={{ color: themeColors.text }}>Current Usage</h3>
                <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(usage, null, 2)}</pre>
              </div>
            )}
            {window && (
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <h3 style={{ color: themeColors.text }}>Rate Limit Window</h3>
                <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(window, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Retry Section */}
      {activeSection === 'retry' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Register Retry Policy</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Policy Name *</label>
                <input value={retryForm.name} onChange={e => setRetryForm({ ...retryForm, name: e.target.value })} placeholder="e.g. llm-default" />
              </div>
              <div className="form-group">
                <label>Max Retries</label>
                <input value={retryForm.max_retries} onChange={e => setRetryForm({ ...retryForm, max_retries: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Base Delay (ms)</label>
                <input value={retryForm.base_delay_ms} onChange={e => setRetryForm({ ...retryForm, base_delay_ms: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Max Delay (ms)</label>
                <input value={retryForm.max_delay_ms} onChange={e => setRetryForm({ ...retryForm, max_delay_ms: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={retryForm.strategy} onChange={e => setRetryForm({ ...retryForm, strategy: e.target.value })}>
                  {RETRY_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Retryable Status Codes</label>
                <input value={retryForm.retryable_status_codes} onChange={e => setRetryForm({ ...retryForm, retryable_status_codes: e.target.value })} placeholder="comma-separated" />
              </div>
            </div>
            <button onClick={handleRegisterRetry} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Policy</button>
          </div>

          {retryPolicies.length > 0 && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <h3 style={{ color: themeColors.text }}>Recent Retry Policies</h3>
              <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
                {retryPolicies.map((p: any) => {
                  const id = p.policy_id ?? p.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{p.name} <span style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>· {id}</span></div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.8 }}>{p.strategy} · max {p.max_retries} · base {p.base_delay_ms}ms · cap {p.max_delay_ms}ms</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Compute Retry Delay</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Policy ID *</label>
                <input value={delayForm.policy_id} onChange={e => setDelayForm({ ...delayForm, policy_id: e.target.value })} placeholder="e.g. pol_xxx" />
              </div>
              <div className="form-group">
                <label>Attempt Number</label>
                <input value={delayForm.attempt_number} onChange={e => setDelayForm({ ...delayForm, attempt_number: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Last Status Code</label>
                <input value={delayForm.last_status_code} onChange={e => setDelayForm({ ...delayForm, last_status_code: e.target.value })} type="number" />
              </div>
            </div>
            <button onClick={handleComputeDelay} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Compute Delay</button>
            {delayResult && (
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12, marginTop: 12 }}>{JSON.stringify(delayResult, null, 2)}</pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default QuotaManagerPanel;
