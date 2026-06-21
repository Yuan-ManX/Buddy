import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface CoordinatorStats {
  coordinator_id: string;
  state: string;
  uptime_seconds: number;
  executions: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number;
  };
  tokens: {
    total: number;
    avg_per_execution: number;
  };
  modes_used: Record<string, number>;
  modules_used: Record<string, number>;
  agents: {
    managed: number;
    active: number;
  };
  modules: Record<string, {
    is_available: boolean;
    is_healthy: boolean;
    error_count: number;
    total_calls: number;
    last_heartbeat: string;
  }>;
  recent_executions: Array<{
    result_id: string;
    mode: string;
    success: boolean;
    duration_ms: number;
    tokens: number;
    timestamp: string;
  }>;
  config: {
    max_concurrent_agents: number;
    execution_timeout_ms: number;
    enable_auto_recovery: boolean;
    enable_telemetry: boolean;
    enable_governance: boolean;
  };
}

interface ExecutionRecord {
  result_id: string;
  mode: string;
  success: boolean;
  content_preview: string;
  error: string;
  tokens: number;
  duration_ms: number;
  modules: string[];
  timestamp: string;
}

export function RuntimeCoordinatorPanel() {
  const [stats, setStats] = useState<CoordinatorStats | null>(null);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [coordinatorState, setCoordinatorState] = useState<string>('uninitialized');
  const [testInput, setTestInput] = useState('');
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [selectedMode, setSelectedMode] = useState('direct');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, statusRes, execRes] = await Promise.all([
        api.coordinator.stats(),
        api.coordinator.status(),
        api.coordinator.executions(20),
      ]);
      setStats(statsRes);
      setCoordinatorState(statusRes.state);
      setExecutions(execRes.executions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load coordinator data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleLifecycle = async (action: string) => {
    try {
      setError(null);
      switch (action) {
        case 'initialize':
          await api.coordinator.initialize();
          break;
        case 'start':
          await api.coordinator.start();
          break;
        case 'pause':
          await api.coordinator.pause();
          break;
        case 'resume':
          await api.coordinator.resume();
          break;
        case 'stop':
          await api.coordinator.stop();
          break;
        case 'reset':
          await api.coordinator.reset();
          break;
      }
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action}`);
    }
  };

  const handleExecute = async () => {
    if (!testInput.trim()) return;
    try {
      setTestLoading(true);
      setTestResult(null);
      const result = await api.coordinator.execute({
        message: testInput,
        agent_name: 'Buddy',
        mode: selectedMode,
        enable_reasoning: selectedMode === 'reasoned',
      });
      setTestResult(JSON.stringify(result, null, 2));
      await loadData();
    } catch (err) {
      setTestResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setTestLoading(false);
    }
  };

  const getStateColor = (state: string): string => {
    switch (state) {
      case 'running': return '#10b981';
      case 'ready': return '#3b82f6';
      case 'paused': return '#f59e0b';
      case 'error': return '#ef4444';
      case 'stopping':
      case 'stopped': return '#6b7280';
      case 'initializing':
      case 'recovering': return '#8b5cf6';
      default: return '#9ca3af';
    }
  };

  const getModuleHealthColor = (healthy: boolean, available: boolean): string => {
    if (!available) return '#6b7280';
    return healthy ? '#10b981' : '#ef4444';
  };

  if (loading) {
    return (
      <div style={{ padding: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
        <div style={{ color: 'var(--text-secondary)' }}>Loading coordinator data...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', overflow: 'auto', maxHeight: 'calc(100vh - 48px)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Runtime Coordinator</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: '14px' }}>
            Central orchestration for all agent capabilities
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '12px', height: '12px', borderRadius: '50%',
            backgroundColor: getStateColor(coordinatorState),
            boxShadow: `0 0 8px ${getStateColor(coordinatorState)}`,
          }} />
          <span style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '14px' }}>{coordinatorState}</span>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '12px 16px', marginBottom: '16px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px',
          color: '#ef4444', fontSize: '14px',
        }}>
          {error}
          <button onClick={() => setError(null)} style={{
            marginLeft: '8px', background: 'none', border: 'none',
            color: '#ef4444', cursor: 'pointer', fontWeight: 600,
          }}>Dismiss</button>
        </div>
      )}

      {/* Lifecycle Controls */}
      <div style={{
        display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap',
        padding: '16px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px',
      }}>
        <button onClick={() => handleLifecycle('initialize')} disabled={coordinatorState !== 'uninitialized'}
          style={controlBtnStyle(coordinatorState === 'uninitialized')}>Initialize</button>
        <button onClick={() => handleLifecycle('start')} disabled={coordinatorState !== 'ready'}
          style={controlBtnStyle(coordinatorState === 'ready')}>Start</button>
        <button onClick={() => handleLifecycle('pause')} disabled={coordinatorState !== 'running'}
          style={controlBtnStyle(coordinatorState === 'running')}>Pause</button>
        <button onClick={() => handleLifecycle('resume')} disabled={coordinatorState !== 'paused'}
          style={controlBtnStyle(coordinatorState === 'paused')}>Resume</button>
        <button onClick={() => handleLifecycle('stop')} disabled={!['running', 'paused', 'ready'].includes(coordinatorState)}
          style={controlBtnStyle(['running', 'paused', 'ready'].includes(coordinatorState))}>Stop</button>
        <button onClick={() => handleLifecycle('reset')}
          style={{ ...controlBtnStyle(true), backgroundColor: '#ef4444' }}>Reset</button>
        <button onClick={loadData} style={{ ...controlBtnStyle(true), backgroundColor: '#6b7280' }}>Refresh</button>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <StatCard label="Total Executions" value={stats?.executions.total || 0} color="#3b82f6" />
        <StatCard label="Success Rate" value={`${((stats?.executions.success_rate || 0) * 100).toFixed(1)}%`} color="#10b981" />
        <StatCard label="Total Tokens" value={stats?.tokens.total || 0} color="#8b5cf6" />
        <StatCard label="Uptime" value={`${(stats?.uptime_seconds || 0).toFixed(0)}s`} color="#f59e0b" />
      </div>

      {/* Test Execution */}
      <div style={{
        padding: '16px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px', marginBottom: '24px',
      }}>
        <h3 style={{ margin: '0 0 12px', fontSize: '16px', fontWeight: 600 }}>Test Execution</h3>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
          <select value={selectedMode} onChange={(e) => setSelectedMode(e.target.value)}
            style={{
              padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: '14px',
            }}>
            <option value="direct">Direct</option>
            <option value="reasoned">Reasoned</option>
            <option value="collaborative">Collaborative</option>
            <option value="autonomous">Autonomous</option>
            <option value="reflective">Reflective</option>
          </select>
          <input
            type="text"
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
            placeholder="Enter a test message..."
            style={{
              flex: 1, padding: '8px 12px', borderRadius: '8px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: '14px',
            }}
          />
          <button onClick={handleExecute} disabled={testLoading || !testInput.trim()}
            style={{
              padding: '8px 16px', borderRadius: '8px', border: 'none',
              backgroundColor: testLoading ? '#6b7280' : '#3b82f6',
              color: 'white', cursor: testLoading ? 'not-allowed' : 'pointer',
              fontWeight: 600, fontSize: '14px',
            }}>{testLoading ? 'Running...' : 'Execute'}</button>
        </div>
        {testResult && (
          <pre style={{
            padding: '12px', backgroundColor: 'var(--bg-primary)', borderRadius: '8px',
            fontSize: '12px', overflow: 'auto', maxHeight: '300px',
            color: 'var(--text-primary)', whiteSpace: 'pre-wrap',
          }}>{testResult}</pre>
        )}
      </div>

      {/* Module Status */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 12px', fontSize: '16px', fontWeight: 600 }}>Module Status</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
          {stats?.modules && Object.entries(stats.modules).map(([name, status]) => (
            <div key={name} style={{
              padding: '12px', backgroundColor: 'var(--bg-secondary)', borderRadius: '8px',
              display: 'flex', flexDirection: 'column', gap: '4px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '14px', textTransform: 'capitalize' }}>
                  {name.replace(/_/g, ' ')}
                </span>
                <div style={{
                  width: '8px', height: '8px', borderRadius: '50%',
                  backgroundColor: getModuleHealthColor(status.is_healthy, status.is_available),
                }} />
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Calls: {status.total_calls} | Errors: {status.error_count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Execution History */}
      <div>
        <h3 style={{ margin: '0 0 12px', fontSize: '16px', fontWeight: 600 }}>Recent Executions</h3>
        <div style={{ overflow: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '8px', textAlign: 'left', color: 'var(--text-secondary)' }}>ID</th>
                <th style={{ padding: '8px', textAlign: 'left', color: 'var(--text-secondary)' }}>Mode</th>
                <th style={{ padding: '8px', textAlign: 'left', color: 'var(--text-secondary)' }}>Status</th>
                <th style={{ padding: '8px', textAlign: 'left', color: 'var(--text-secondary)' }}>Modules</th>
                <th style={{ padding: '8px', textAlign: 'right', color: 'var(--text-secondary)' }}>Tokens</th>
                <th style={{ padding: '8px', textAlign: 'right', color: 'var(--text-secondary)' }}>Duration</th>
                <th style={{ padding: '8px', textAlign: 'right', color: 'var(--text-secondary)' }}>Time</th>
              </tr>
            </thead>
            <tbody>
              {executions.map((exec) => (
                <tr key={exec.result_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '12px' }}>{exec.result_id.slice(0, 12)}</td>
                  <td style={{ padding: '8px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '4px', fontSize: '12px',
                      backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6',
                    }}>{exec.mode}</span>
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span style={{ color: exec.success ? '#10b981' : '#ef4444' }}>
                      {exec.success ? 'Success' : 'Failed'}
                    </span>
                    {exec.error && <div style={{ fontSize: '11px', color: '#ef4444' }}>{exec.error.slice(0, 60)}</div>}
                  </td>
                  <td style={{ padding: '8px', fontSize: '12px' }}>{exec.modules.join(', ')}</td>
                  <td style={{ padding: '8px', textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>{exec.tokens}</td>
                  <td style={{ padding: '8px', textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>{exec.duration_ms.toFixed(0)}ms</td>
                  <td style={{ padding: '8px', textAlign: 'right', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {new Date(exec.timestamp).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
              {executions.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No executions yet. Use the test panel above to start.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{
      padding: '16px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px',
      borderLeft: `3px solid ${color}`,
    }}>
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>{label}</div>
      <div style={{ fontSize: '24px', fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function controlBtnStyle(enabled: boolean): React.CSSProperties {
  return {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: enabled ? '#3b82f6' : '#374151',
    color: enabled ? 'white' : '#6b7280',
    cursor: enabled ? 'pointer' : 'not-allowed',
    fontWeight: 600,
    fontSize: '13px',
    opacity: enabled ? 1 : 0.5,
  };
}