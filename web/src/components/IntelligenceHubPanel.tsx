import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

// ── Inline Types ──

interface IntelligenceSignal {
  signal_id: string;
  name: string;
  source: string;
  signal_type: string;
  content: string;
  severity: string;
  confidence: number;
  status: string;
  ingested_at: string;
}

interface IntelligencePattern {
  pattern_id: string;
  name: string;
  description: string;
  pattern_type: string;
  signal_count: number;
  confidence: number;
  status: string;
  detected_at: string;
}

interface IntelligenceReport {
  report_id: string;
  title: string;
  summary: string;
  pattern_count: number;
  signal_count: number;
  severity: string;
  status: string;
  generated_at: string;
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

export const IntelligenceHubPanel: React.FC = () => {
  const toast = useToast();

  const [signals, setSignals] = useState<IntelligenceSignal[]>([]);
  const [patterns, setPatterns] = useState<IntelligencePattern[]>([]);
  const [reports, setReports] = useState<IntelligenceReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'ingest' | 'signals' | 'patterns' | 'reports'>('overview');

  // Ingest form
  const [ingestForm, setIngestForm] = useState({
    name: '',
    source: '',
    signal_type: 'event',
    content: '',
    severity: 'info',
    confidence: 0.8,
  });
  const [ingesting, setIngesting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, p, r] = await Promise.all([
        request<IntelligenceSignal[]>('/intelligence-hub/signals').catch(() => []),
        request<IntelligencePattern[]>('/intelligence-hub/patterns').catch(() => []),
        request<IntelligenceReport[]>('/intelligence-hub/reports').catch(() => []),
      ]);
      setSignals(Array.isArray(s) ? s : (s as any)?.signals || []);
      setPatterns(Array.isArray(p) ? p : (p as any)?.patterns || []);
      setReports(Array.isArray(r) ? r : (r as any)?.reports || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load intelligence hub data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleIngest = async () => {
    if (!ingestForm.name.trim() || !ingestForm.content.trim()) return;
    try {
      setIngesting(true);
      const result = await request<any>('/intelligence-hub/signals', {
        method: 'POST',
        body: JSON.stringify({
          name: ingestForm.name,
          source: ingestForm.source || undefined,
          signal_type: ingestForm.signal_type,
          content: ingestForm.content,
          severity: ingestForm.severity,
          confidence: ingestForm.confidence,
        }),
      });
      toast.success(result.message || 'Signal ingested successfully');
      setIngestForm({ name: '', source: '', signal_type: 'event', content: '', severity: 'info', confidence: 0.8 });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setIngesting(false);
    }
  };

  const severityColors: Record<string, string> = {
    info: '#3b82f6',
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
    critical: '#dc2626',
  };

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    new: '#3b82f6',
    acknowledged: '#f59e0b',
    resolved: '#22c55e',
    dismissed: '#9ca3af',
    archived: '#9ca3af',
    generating: '#8b5cf6',
  };

  const confidenceColor = (c: number): string => {
    if (c >= 0.8) return '#22c55e';
    if (c >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Intelligence Hub</h2>
          <p className="panel-subtitle">Ingest signals, detect patterns, and generate intelligence reports</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading intelligence hub data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Intelligence Hub</h2>
        <p className="panel-subtitle">Signal ingestion, pattern detection, and intelligence reporting</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat-item">
          <div className="stat-content">
            <span className="stat-value">{signals.length}</span>
            <span className="stat-label">Signals</span>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-content">
            <span className="stat-value" style={{ color: '#22c55e' }}>{patterns.length}</span>
            <span className="stat-label">Patterns</span>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-content">
            <span className="stat-value" style={{ color: '#8b5cf6' }}>{reports.length}</span>
            <span className="stat-label">Reports</span>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-content">
            <span className="stat-value" style={{ color: '#ef4444' }}>
              {signals.filter(s => s.severity === 'high' || s.severity === 'critical').length}
            </span>
            <span className="stat-label">High Severity</span>
          </div>
        </div>
        <div className="stat-item">
          <div className="stat-content">
            <span className="stat-value" style={{ color: '#3b82f6' }}>
              {signals.filter(s => s.status === 'new').length}
            </span>
            <span className="stat-label">New</span>
          </div>
        </div>
      </div>

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'ingest', 'signals', 'patterns', 'reports'] as const).map(s => (
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
          <h3>Hub Overview</h3>
          <div className="dashboard-stat-row">
            <span>Total Signals</span>
            <strong>{signals.length}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Detected Patterns</span>
            <strong style={{ color: '#22c55e' }}>{patterns.length}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>Generated Reports</span>
            <strong style={{ color: '#8b5cf6' }}>{reports.length}</strong>
          </div>
          <div className="dashboard-stat-row">
            <span>High/Critical Signals</span>
            <strong style={{ color: '#ef4444' }}>
              {signals.filter(s => s.severity === 'high' || s.severity === 'critical').length}
            </strong>
          </div>
          <div className="dashboard-stat-row">
            <span>New Signals</span>
            <strong style={{ color: '#3b82f6' }}>
              {signals.filter(s => s.status === 'new').length}
            </strong>
          </div>

          <h3 style={{ marginTop: 24 }}>Recent Patterns</h3>
          {patterns.length === 0 ? (
            <div className="panel-empty">No patterns detected yet</div>
          ) : (
            <div className="forge-skill-list">
              {patterns.slice(0, 5).map(pattern => (
                <div key={pattern.pattern_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{pattern.name}</div>
                    <span className="dashboard-badge" style={{
                      background: confidenceColor(pattern.confidence),
                      color: '#fff',
                    }}>
                      {Math.round(pattern.confidence * 100)}%
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{pattern.description}</div>
                    <div>Type: {pattern.pattern_type} | Signals: {pattern.signal_count}</div>
                    <div>Detected: {new Date(pattern.detected_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <h3 style={{ marginTop: 24 }}>Recent Reports</h3>
          {reports.length === 0 ? (
            <div className="panel-empty">No reports generated yet</div>
          ) : (
            <div className="forge-skill-list">
              {reports.slice(0, 3).map(report => (
                <div key={report.report_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{report.title}</div>
                    <span className="dashboard-badge" style={{
                      background: severityColors[report.severity] || '#9ca3af',
                      color: '#fff',
                    }}>
                      {report.severity}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{report.summary}</div>
                    <div>Patterns: {report.pattern_count} | Signals: {report.signal_count}</div>
                    <div>Generated: {new Date(report.generated_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Ingest Section ── */}
      {activeSection === 'ingest' && (
        <div className="dashboard-section">
          <h3>Ingest Signal</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Signal Name</label>
              <input
                type="text"
                value={ingestForm.name}
                onChange={e => setIngestForm(f => ({ ...f, name: e.target.value }))}
                placeholder="My Signal"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Source</label>
                <input
                  type="text"
                  value={ingestForm.source}
                  onChange={e => setIngestForm(f => ({ ...f, source: e.target.value }))}
                  placeholder="e.g., system_monitor, user_feedback"
                />
              </div>
              <div className="form-group">
                <label>Signal Type</label>
                <select
                  value={ingestForm.signal_type}
                  onChange={e => setIngestForm(f => ({ ...f, signal_type: e.target.value }))}
                >
                  <option value="event">Event</option>
                  <option value="anomaly">Anomaly</option>
                  <option value="trend">Trend</option>
                  <option value="alert">Alert</option>
                  <option value="metric">Metric</option>
                  <option value="log">Log</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={4}
                value={ingestForm.content}
                onChange={e => setIngestForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Enter the signal content or description..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Severity</label>
                <select
                  value={ingestForm.severity}
                  onChange={e => setIngestForm(f => ({ ...f, severity: e.target.value }))}
                >
                  <option value="info">Info</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="form-group">
                <label>Confidence ({ingestForm.confidence})</label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={ingestForm.confidence}
                  onChange={e => setIngestForm(f => ({ ...f, confidence: parseFloat(e.target.value) }))}
                />
              </div>
            </div>
            <button
              className="btn-primary"
              onClick={handleIngest}
              disabled={ingesting || !ingestForm.name.trim() || !ingestForm.content.trim()}
            >
              {ingesting ? 'Ingesting...' : 'Ingest Signal'}
            </button>
          </div>
        </div>
      )}

      {/* ── Signals Section ── */}
      {activeSection === 'signals' && (
        <div className="dashboard-section">
          <h3>Signals ({signals.length})</h3>
          {signals.length === 0 ? (
            <div className="panel-empty">No signals ingested yet. Go to the Ingest tab to add one.</div>
          ) : (
            <div className="forge-skill-list">
              {signals.map(signal => (
                <div key={signal.signal_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{signal.name}</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <span className="dashboard-badge" style={{
                        background: severityColors[signal.severity] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {signal.severity}
                      </span>
                      <span className="dashboard-badge" style={{
                        background: statusColors[signal.status] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {signal.status}
                      </span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Source: {signal.source} | Type: {signal.signal_type}</div>
                    <div style={{ marginTop: 4, fontSize: '0.85rem', color: '#6b7280' }}>
                      {signal.content}
                    </div>
                    <div style={{ marginTop: 4 }}>
                      Confidence:{' '}
                      <span style={{ color: confidenceColor(signal.confidence), fontWeight: 600 }}>
                        {Math.round(signal.confidence * 100)}%
                      </span>
                    </div>
                    <div>Ingested: {new Date(signal.ingested_at).toLocaleString()}</div>
                    <div>Signal ID: {signal.signal_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Patterns Section ── */}
      {activeSection === 'patterns' && (
        <div className="dashboard-section">
          <h3>Detected Patterns ({patterns.length})</h3>
          {patterns.length === 0 ? (
            <div className="panel-empty">No patterns detected yet</div>
          ) : (
            <div className="forge-skill-list">
              {patterns.map(pattern => (
                <div key={pattern.pattern_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{pattern.name}</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <span className="dashboard-badge" style={{
                        background: confidenceColor(pattern.confidence),
                        color: '#fff',
                      }}>
                        {Math.round(pattern.confidence * 100)}%
                      </span>
                      <span className="dashboard-badge" style={{
                        background: statusColors[pattern.status] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {pattern.status}
                      </span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{pattern.description}</div>
                    <div>Type: {pattern.pattern_type} | Signals: {pattern.signal_count}</div>
                    <div>Detected: {new Date(pattern.detected_at).toLocaleString()}</div>
                    <div>Pattern ID: {pattern.pattern_id}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Reports Section ── */}
      {activeSection === 'reports' && (
        <div className="dashboard-section">
          <h3>Intelligence Reports ({reports.length})</h3>
          {reports.length === 0 ? (
            <div className="panel-empty">No reports generated yet</div>
          ) : (
            <div className="forge-skill-list">
              {reports.map(report => (
                <div key={report.report_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{report.title}</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <span className="dashboard-badge" style={{
                        background: severityColors[report.severity] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {report.severity}
                      </span>
                      <span className="dashboard-badge" style={{
                        background: statusColors[report.status] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {report.status}
                      </span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{report.summary}</div>
                    <div>Patterns: {report.pattern_count} | Signals: {report.signal_count}</div>
                    <div>Generated: {new Date(report.generated_at).toLocaleString()}</div>
                    <div>Report ID: {report.report_id}</div>
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

export default IntelligenceHubPanel;