// SystemHealthPanel: real-time system health and metrics dashboard.
//
// Polls /api/v1/system/metrics every 5 seconds and renders:
//   - Top-level status cards (uptime, request count, error rate)
//   - Pure-SVG sparkline of recent request volume
//   - Per-endpoint request counts (top 10)
//   - Cognitive event counters by engine
//
// No external charting library — all visuals are hand-rolled SVG.

import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface MetricsPayload {
  requests_total: number;
  requests_by_endpoint: Record<string, number>;
  requests_by_status: Record<string, number>;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  cognitive_events_total: number;
  cognitive_events_by_engine: Record<string, number>;
  cognitive_events_by_type: Record<string, number>;
  agent_executions_total: number;
  agent_executions_by_agent: Record<string, number>;
  agent_failures_total: number;
  active_traces: number;
  uptime_seconds: number;
}

interface HealthPayload {
  status: string;
  uptime_s: number;
  agent_count: number;
  cognitive_engine_count: number;
  db_connected: boolean;
  version: string;
  timestamp: string;
}

const POLL_MS = 5000;
const HISTORY_LEN = 30;

export const SystemHealthPanel: React.FC = () => {
  const toast = useToast();
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [metrics, setMetrics] = useState<MetricsPayload | null>(null);
  const [history, setHistory] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadAll = async () => {
    try {
      const [h, m] = await Promise.all([
        api.systemV1.health(),
        api.systemV1.metrics(),
      ]);
      setHealth(h);
      setMetrics(m);
      setHistory(prev => [...prev.slice(-(HISTORY_LEN - 1)), m.requests_total]);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load system metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    timerRef.current = setInterval(loadAll, POLL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const formatUptime = (s: number) => {
    if (s < 60) return `${s.toFixed(1)}s`;
    if (s < 3600) return `${(s / 60).toFixed(1)}m`;
    return `${(s / 3600).toFixed(1)}h`;
  };

  const topEndpoints = metrics
    ? Object.entries(metrics.requests_by_endpoint)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
    : [];

  const topCognitive = metrics
    ? Object.entries(metrics.cognitive_events_by_engine)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
    : [];

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>📊 System Health</h2>
          <p className="panel-subtitle">Loading system metrics...</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Fetching metrics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>📊 System Health</h2>
        <p className="panel-subtitle">
          Real-time process metrics and health. Auto-refreshes every 5s.
        </p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadAll} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Top-level status cards */}
      <div className="stats-bar" style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div className="stat-item">
          <div className="stat-label">Status</div>
          <div className="stat-value" style={{ color: health?.status === 'ok' ? '#10b981' : '#f59e0b' }}>
            {health?.status || 'unknown'}
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Uptime</div>
          <div className="stat-value">{formatUptime(health?.uptime_s || 0)}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Requests</div>
          <div className="stat-value">{metrics?.requests_total ?? 0}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">p50 / p99</div>
          <div className="stat-value">
            {(metrics?.p50_ms ?? 0).toFixed(1)} / {(metrics?.p99_ms ?? 0).toFixed(1)} ms
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Cognitive Events</div>
          <div className="stat-value">{metrics?.cognitive_events_total ?? 0}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Active Traces</div>
          <div className="stat-value">{metrics?.active_traces ?? 0}</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">DB</div>
          <div className="stat-value" style={{ color: health?.db_connected ? '#10b981' : '#ef4444' }}>
            {health?.db_connected ? 'connected' : 'down'}
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Engines</div>
          <div className="stat-value">{health?.cognitive_engine_count ?? 0}</div>
        </div>
      </div>

      {/* Sparkline of request volume */}
      <div style={{ marginTop: 24 }}>
        <h3 style={{ marginBottom: 8 }}>Request Volume (last {HISTORY_LEN} polls)</h3>
        <Sparkline values={history} width={640} height={80} />
      </div>

      {/* Top endpoints */}
      <div style={{ marginTop: 24, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div>
          <h3 style={{ marginBottom: 8 }}>Top Endpoints</h3>
          {topEndpoints.length === 0 ? (
            <p style={{ color: '#6b7280', fontSize: 13 }}>No endpoint traffic recorded yet.</p>
          ) : (
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                  <th style={{ padding: '4px 8px' }}>Endpoint</th>
                  <th style={{ padding: '4px 8px', textAlign: 'right' }}>Count</th>
                </tr>
              </thead>
              <tbody>
                {topEndpoints.map(([ep, count]) => (
                  <tr key={ep} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '4px 8px', fontFamily: 'monospace' }}>{ep}</td>
                    <td style={{ padding: '4px 8px', textAlign: 'right' }}>{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div>
          <h3 style={{ marginBottom: 8 }}>Cognitive Events by Engine</h3>
          {topCognitive.length === 0 ? (
            <p style={{ color: '#6b7280', fontSize: 13 }}>No cognitive events recorded yet.</p>
          ) : (
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>
                  <th style={{ padding: '4px 8px' }}>Engine</th>
                  <th style={{ padding: '4px 8px', textAlign: 'right' }}>Events</th>
                </tr>
              </thead>
              <tbody>
                {topCognitive.map(([eng, count]) => (
                  <tr key={eng} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '4px 8px', fontFamily: 'monospace' }}>{eng}</td>
                    <td style={{ padding: '4px 8px', textAlign: 'right' }}>{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Status code breakdown */}
      {metrics && Object.keys(metrics.requests_by_status).length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3 style={{ marginBottom: 8 }}>Status Codes</h3>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {Object.entries(metrics.requests_by_status).map(([bucket, count]) => {
              const color =
                bucket === '2xx' ? '#10b981' :
                bucket === '3xx' ? '#3b82f6' :
                bucket === '4xx' ? '#f59e0b' : '#ef4444';
              return (
                <span key={bucket} style={{
                  display: 'inline-block',
                  padding: '4px 12px',
                  borderRadius: 12,
                  background: color,
                  color: '#fff',
                  fontSize: 12,
                  fontWeight: 600,
                }}>
                  {bucket}: {count}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {health && (
        <div style={{ marginTop: 24, fontSize: 11, color: '#6b7280' }}>
          Version {health.version} · Last refresh {new Date().toLocaleTimeString()} ·
          Timestamp {health.timestamp}
        </div>
      )}
    </div>
  );
};

// ── Pure-SVG sparkline ──────────────────────────────────────────

const Sparkline: React.FC<{ values: number[]; width: number; height: number }> = ({
  values,
  width,
  height,
}) => {
  if (values.length < 2) {
    return (
      <div style={{ width, height, background: '#f9fafb', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 11 }}>
        Collecting data...
      </div>
    );
  }
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const stepX = width / (values.length - 1);
  const points = values.map((v, i) => {
    const x = i * stepX;
    const y = height - ((v - min) / range) * (height - 8) - 4;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const path = `M ${points.join(' L ')}`;
  const areaPath = `${path} L ${width},${height} L 0,${height} Z`;
  return (
    <svg width={width} height={height} style={{ background: '#f9fafb', borderRadius: 4 }}>
      <path d={areaPath} fill="#dbeafe" />
      <path d={path} fill="none" stroke="#3b82f6" strokeWidth={1.5} />
      {values.map((v, i) => {
        const [x, y] = points[i].split(',').map(Number);
        return <circle key={i} cx={x} cy={y} r={1.5} fill="#1d4ed8" />;
      })}
    </svg>
  );
};
