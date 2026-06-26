import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface ResilienceReport {
  total_components: number;
  healthy: number;
  degraded: number;
  unhealthy: number;
  uptime_percentage: number;
  recent_failures: number;
  recovery_success_rate: number;
}

interface ComponentRegistration {
  component_id: string;
  component_type: string;
  health_check_url?: string;
  status: string;
  registered_at: string;
}

interface HealthStatus {
  component_id: string;
  status: string;
  response_time_ms: number;
  error_count: number;
  uptime_percentage: number;
  consecutive_failures: number;
}

interface FailureReport {
  failure_id: string;
  component_id: string;
  failure_type: string;
  severity: string;
  root_cause: string;
  affected_services: string[];
  recovery_status: string;
  occurred_at: string;
}

interface SimulationResult {
  detected: boolean;
  recovery_triggered: boolean;
  recovery_success: boolean;
  time_to_detect_ms: number;
  time_to_recover_ms: number;
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

export const PlatformResiliencePanel: React.FC = () => {
  const toast = useToast();

  const [activeTab, setActiveTab] = useState<'overview' | 'register' | 'health' | 'failures' | 'simulate'>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overview
  const [report, setReport] = useState<ResilienceReport | null>(null);

  // Register
  const [registerForm, setRegisterForm] = useState({
    component_id: '',
    component_type: 'agent',
    health_check_url: '',
  });
  const [registering, setRegistering] = useState(false);
  const [registeredComponent, setRegisteredComponent] = useState<ComponentRegistration | null>(null);

  // Health
  const [healthComponentId, setHealthComponentId] = useState('');
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);

  // Failures
  const [failures, setFailures] = useState<FailureReport[]>([]);
  const [failuresLoading, setFailuresLoading] = useState(false);
  const [recoveringId, setRecoveringId] = useState<string | null>(null);

  // Simulate
  const [simulateForm, setSimulateForm] = useState({
    component_id: '',
    failure_type: 'timeout',
  });
  const [simulating, setSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);

  const loadReport = useCallback(async () => {
    try {
      setLoading(true);
      const r = await request<ResilienceReport>('/platform-resilience/report');
      setReport(r);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load resilience report');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFailures = useCallback(async () => {
    try {
      setFailuresLoading(true);
      const f = await request<FailureReport[]>('/platform-resilience/failures');
      setFailures(Array.isArray(f) ? f : (f as any)?.failures || []);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setFailuresLoading(false);
    }
  }, [toast]);

  useEffect(() => { loadReport(); }, [loadReport]);

  const handleRegister = async () => {
    if (!registerForm.component_id.trim()) return;
    try {
      setRegistering(true);
      const result = await request<ComponentRegistration>('/platform-resilience/register', {
        method: 'POST',
        body: JSON.stringify({
          component_id: registerForm.component_id,
          component_type: registerForm.component_type,
          health_check_url: registerForm.health_check_url || undefined,
        }),
      });
      setRegisteredComponent(result);
      toast.success('Component registered successfully');
      setRegisterForm({ component_id: '', component_type: 'agent', health_check_url: '' });
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRegistering(false);
    }
  };

  const handleHealthCheck = async () => {
    if (!healthComponentId.trim()) return;
    try {
      setHealthLoading(true);
      const result = await request<HealthStatus>(`/platform-resilience/health/${healthComponentId}`);
      setHealthStatus(result);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setHealthLoading(false);
    }
  };

  const handleRecover = async (failureId: string) => {
    try {
      setRecoveringId(failureId);
      await request(`/platform-resilience/recover/${failureId}`, { method: 'POST' });
      toast.success('Recovery triggered successfully');
      loadFailures();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRecoveringId(null);
    }
  };

  const handleSimulate = async () => {
    if (!simulateForm.component_id.trim()) return;
    try {
      setSimulating(true);
      const result = await request<SimulationResult>('/platform-resilience/simulate', {
        method: 'POST',
        body: JSON.stringify({
          component_id: simulateForm.component_id,
          failure_type: simulateForm.failure_type,
        }),
      });
      setSimulationResult(result);
      toast.success('Failure simulation completed');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSimulating(false);
    }
  };

  const statusColors: Record<string, string> = {
    HEALTHY: '#22c55e',
    DEGRADED: '#f59e0b',
    UNHEALTHY: '#ef4444',
    healthy: '#22c55e',
    degraded: '#f59e0b',
    unhealthy: '#ef4444',
  };

  const severityColors: Record<string, string> = {
    critical: '#ef4444',
    high: '#f97316',
    medium: '#f59e0b',
    low: '#3b82f6',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Platform Resilience Engine</h2>
          <p className="panel-subtitle">Monitor, detect, and recover from platform failures automatically</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading platform resilience data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Platform Resilience Engine</h2>
        <p className="panel-subtitle">Monitor, detect, and recover from platform failures automatically</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadReport} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {report && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{report.total_components}</span>
              <span className="stat-label">Total Components</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{report.healthy}</span>
              <span className="stat-label">Healthy</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>{report.degraded}</span>
              <span className="stat-label">Degraded</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#ef4444' }}>{report.unhealthy}</span>
              <span className="stat-label">Unhealthy</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: report.uptime_percentage >= 99 ? '#22c55e' : '#f59e0b' }}>
                {report.uptime_percentage.toFixed(1)}%
              </span>
              <span className="stat-label">Uptime</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'register', 'health', 'failures', 'simulate'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeTab === s ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(s);
              if (s === 'failures') loadFailures();
            }}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {activeTab === 'overview' && report && (
        <div className="dashboard-section">
          <h3>Resilience Overview</h3>
          <div className="dashboard-stat-row">
            <span>Total Components</span>
            <strong>{report.total_components}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Healthy</span>
            <strong style={{ color: '#22c55e' }}>{report.healthy}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Degraded</span>
            <strong style={{ color: '#f59e0b' }}>{report.degraded}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Unhealthy</span>
            <strong style={{ color: '#ef4444' }}>{report.unhealthy}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Uptime Percentage</span>
            <strong style={{ color: report.uptime_percentage >= 99 ? '#22c55e' : '#f59e0b' }}>
              {report.uptime_percentage.toFixed(1)}%
            </strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Recent Failures</span>
            <strong style={{ color: report.recent_failures > 0 ? '#ef4444' : '#22c55e' }}>
              {report.recent_failures}
            </strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Recovery Success Rate</span>
            <strong style={{ color: report.recovery_success_rate >= 0.8 ? '#22c55e' : '#f59e0b' }}>
              {(report.recovery_success_rate * 100).toFixed(1)}%
            </strong>
          </div>
        </div>
      )}

      {/* ── Register Tab ── */}
      {activeTab === 'register' && (
        <div className="dashboard-section">
          <h3>Register Component</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Component ID</label>
              <input
                type="text"
                value={registerForm.component_id}
                onChange={e => setRegisterForm(f => ({ ...f, component_id: e.target.value }))}
                placeholder="e.g. agent-orchestrator"
              />
            </div>
            <div className="form-group">
              <label>Component Type</label>
              <select
                value={registerForm.component_type}
                onChange={e => setRegisterForm(f => ({ ...f, component_type: e.target.value }))}
              >
                <option value="agent">Agent</option>
                <option value="tool">Tool</option>
                <option value="api">API</option>
                <option value="database">Database</option>
                <option value="cache">Cache</option>
                <option value="queue">Queue</option>
                <option value="stream">Stream</option>
                <option value="model_endpoint">Model Endpoint</option>
              </select>
            </div>
            <div className="form-group">
              <label>Health Check URL (optional)</label>
              <input
                type="text"
                value={registerForm.health_check_url}
                onChange={e => setRegisterForm(f => ({ ...f, health_check_url: e.target.value }))}
                placeholder="https://example.com/health"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleRegister}
              disabled={registering || !registerForm.component_id.trim()}
            >
              {registering ? 'Registering...' : 'Register'}
            </button>
          </div>

          {registeredComponent && (
            <div className="forge-skill-list">
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">{registeredComponent.component_id}</div>
                  <span className="dashboard-badge" style={{
                    background: statusColors[registeredComponent.status] || '#9ca3af',
                    color: '#fff',
                  }}>
                    {registeredComponent.status}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div>Type: {registeredComponent.component_type}</div>
                  {registeredComponent.health_check_url && (
                    <div>Health Check: {registeredComponent.health_check_url}</div>
                  )}
                  <div>Registered: {new Date(registeredComponent.registered_at).toLocaleString()}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Health Tab ── */}
      {activeTab === 'health' && (
        <div className="dashboard-section">
          <h3>Check Component Health</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Component ID</label>
              <input
                type="text"
                value={healthComponentId}
                onChange={e => setHealthComponentId(e.target.value)}
                placeholder="Enter component ID..."
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleHealthCheck}
              disabled={healthLoading || !healthComponentId.trim()}
            >
              {healthLoading ? 'Checking...' : 'Check Health'}
            </button>
          </div>

          {healthStatus && (
            <div className="forge-skill-list">
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">{healthStatus.component_id}</div>
                  <span className="dashboard-badge" style={{
                    background: statusColors[healthStatus.status] || '#9ca3af',
                    color: '#fff',
                  }}>
                    {healthStatus.status}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div className="dashboard-stat-row">
                    <span>Status</span>
                    <strong style={{ color: statusColors[healthStatus.status] || '#9ca3af' }}>
                      {healthStatus.status}
                    </strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Response Time</span>
                    <strong>{healthStatus.response_time_ms.toFixed(1)}ms</strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Error Count</span>
                    <strong style={{ color: healthStatus.error_count > 0 ? '#ef4444' : '#22c55e' }}>
                      {healthStatus.error_count}
                    </strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Uptime %</span>
                    <strong style={{ color: healthStatus.uptime_percentage >= 99 ? '#22c55e' : '#f59e0b' }}>
                      {healthStatus.uptime_percentage.toFixed(1)}%
                    </strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Consecutive Failures</span>
                    <strong style={{ color: healthStatus.consecutive_failures > 0 ? '#ef4444' : '#22c55e' }}>
                      {healthStatus.consecutive_failures}
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Failures Tab ── */}
      {activeTab === 'failures' && (
        <div className="dashboard-section">
          <h3>Failure Reports</h3>
          {failuresLoading ? (
            <div className="panel-loading">
              <div className="spinner" />
              <span>Loading failures...</span>
            </div>
          ) : failures.length === 0 ? (
            <div className="panel-empty">No failure reports recorded</div>
          ) : (
            <div className="forge-skill-list">
              {failures.map(failure => (
                <div key={failure.failure_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{failure.component_id}</div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <span className="dashboard-badge" style={{
                        background: severityColors[failure.severity] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {failure.severity}
                      </span>
                      <span className="dashboard-badge" style={{
                        background: failure.recovery_status === 'recovered' ? '#22c55e' : '#f59e0b',
                        color: '#fff',
                      }}>
                        {failure.recovery_status}
                      </span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Failure Type: {failure.failure_type}</div>
                    <div>Root Cause: {failure.root_cause}</div>
                    <div>Affected Services: {failure.affected_services.join(', ')}</div>
                    <div>Occurred: {new Date(failure.occurred_at).toLocaleString()}</div>
                    <div style={{ marginTop: 8 }}>
                      <button
                        className="btn-primary"
                        style={{ background: '#f97316' }}
                        onClick={() => handleRecover(failure.failure_id)}
                        disabled={recoveringId === failure.failure_id}
                      >
                        {recoveringId === failure.failure_id ? 'Recovering...' : 'Recover'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Simulate Tab ── */}
      {activeTab === 'simulate' && (
        <div className="dashboard-section">
          <h3>Simulate Failure</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Component ID</label>
              <input
                type="text"
                value={simulateForm.component_id}
                onChange={e => setSimulateForm(f => ({ ...f, component_id: e.target.value }))}
                placeholder="e.g. agent-orchestrator"
              />
            </div>
            <div className="form-group">
              <label>Failure Type</label>
              <select
                value={simulateForm.failure_type}
                onChange={e => setSimulateForm(f => ({ ...f, failure_type: e.target.value }))}
              >
                <option value="timeout">Timeout</option>
                <option value="crash">Crash</option>
                <option value="memory_leak">Memory Leak</option>
                <option value="deadlock">Deadlock</option>
                <option value="network_partition">Network Partition</option>
                <option value="corrupted_state">Corrupted State</option>
                <option value="overload">Overload</option>
              </select>
            </div>
            <button
              className="btn-primary"
              onClick={handleSimulate}
              disabled={simulating || !simulateForm.component_id.trim()}
              style={{ background: '#ef4444' }}
            >
              {simulating ? 'Simulating...' : 'Simulate Failure'}
            </button>
          </div>

          {simulationResult && (
            <div className="forge-skill-list">
              <div className="forge-skill-card">
                <div className="forge-skill-header">
                  <div className="forge-skill-name">Simulation Result</div>
                  <span className="dashboard-badge" style={{
                    background: simulationResult.recovery_success ? '#22c55e' : '#ef4444',
                    color: '#fff',
                  }}>
                    {simulationResult.recovery_success ? 'Recovered' : 'Failed'}
                  </span>
                </div>
                <div className="forge-skill-meta">
                  <div className="dashboard-stat-row">
                    <span>Detected</span>
                    <strong style={{ color: simulationResult.detected ? '#22c55e' : '#ef4444' }}>
                      {simulationResult.detected ? 'Yes' : 'No'}
                    </strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Recovery Triggered</span>
                    <strong style={{ color: simulationResult.recovery_triggered ? '#22c55e' : '#f59e0b' }}>
                      {simulationResult.recovery_triggered ? 'Yes' : 'No'}
                    </strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Recovery Success</span>
                    <strong style={{ color: simulationResult.recovery_success ? '#22c55e' : '#ef4444' }}>
                      {simulationResult.recovery_success ? 'Yes' : 'No'}
                    </strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Time to Detect</span>
                    <strong>{simulationResult.time_to_detect_ms.toFixed(1)}ms</strong>
                  </div>
                  <div className="dashboard-stat-row">
                    <span>Time to Recover</span>
                    <strong>{simulationResult.time_to_recover_ms.toFixed(1)}ms</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PlatformResiliencePanel;