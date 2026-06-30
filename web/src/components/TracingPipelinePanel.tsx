import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: blue/cyan for distributed tracing
const themeColors = {
  primary: '#0ea5e9',
  secondary: '#38bdf8',
  bg: '#f0f9ff',
  border: '#bae6fd',
  accent: '#e0f2fe',
  text: '#0c4a6e',
};

const SPAN_KINDS = ['internal', 'server', 'client', 'producer', 'consumer'];
const SPAN_STATUSES = ['ok', 'error', 'cancelled'];
const EVENT_LEVELS = ['info', 'warning', 'error'];

export const TracingPipelinePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'trace' | 'span'>('overview');

  // Trace list / detail
  const [traces, setTraces] = useState<any[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string>('');
  const [traceDetail, setTraceDetail] = useState<any>(null);
  const [traceSummary, setTraceSummary] = useState<any>(null);

  // Span detail
  const [selectedSpanId, setSelectedSpanId] = useState<string>('');
  const [spanDetail, setSpanDetail] = useState<any>(null);

  // Trace creation form
  const [traceForm, setTraceForm] = useState({
    root_span_name: '',
    agent_id: '',
    resource: '',
  });

  // Span creation form
  const [spanForm, setSpanForm] = useState({
    name: '',
    parent_span_id: '',
    kind: 'internal',
    agent_id: '',
    resource: '',
  });

  // Event form
  const [eventForm, setEventForm] = useState({ name: '', level: 'info', payload: '' });

  // Attribute form
  const [attrForm, setAttrForm] = useState({ key: '', value: '' });

  // Link form
  const [linkForm, setLinkForm] = useState({
    linked_trace_id: '',
    linked_span_id: '',
    relationship: 'follows_from',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.tracingPipeline.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load tracing pipeline stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTraces = useCallback(async () => {
    try {
      const result = await api.tracingPipeline.listTraces({ limit: 50 });
      const list = Array.isArray(result) ? result : (result?.traces ?? []);
      setTraces(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load traces');
    }
  }, [toast]);

  const loadTraceDetail = useCallback(async (traceId: string) => {
    if (!traceId) return;
    try {
      const detail = await api.tracingPipeline.getTrace(traceId);
      setTraceDetail(detail);
      const summary = await api.tracingPipeline.getSummary(traceId).catch(() => null);
      setTraceSummary(summary);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load trace detail');
    }
  }, [toast]);

  const loadSpanDetail = useCallback(async (spanId: string) => {
    if (!spanId) return;
    try {
      const detail = await api.tracingPipeline.getSpan(spanId);
      setSpanDetail(detail);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load span detail');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats and traces when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadTraces();
    }
  }, [activeSection, loadStats, loadTraces]);

  // When trace is selected, load its detail
  useEffect(() => {
    if (selectedTraceId) loadTraceDetail(selectedTraceId);
  }, [selectedTraceId, loadTraceDetail]);

  // When span is selected, load its detail
  useEffect(() => {
    if (selectedSpanId) loadSpanDetail(selectedSpanId);
  }, [selectedSpanId, loadSpanDetail]);

  const handleStartTrace = async () => {
    if (!traceForm.root_span_name.trim()) {
      toast.error('Root span name is required');
      return;
    }
    try {
      const result = await api.tracingPipeline.startTrace({
        root_span_name: traceForm.root_span_name.trim(),
        agent_id: traceForm.agent_id.trim() || undefined,
        resource: traceForm.resource.trim() || undefined,
      });
      const newId = result?.trace_id ?? result?.id;
      toast.success(`Trace started: ${newId ?? ''}`);
      setTraceForm({ root_span_name: '', agent_id: '', resource: '' });
      await loadTraces();
      if (newId) setSelectedTraceId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleStartSpan = async () => {
    if (!selectedTraceId || !spanForm.name.trim()) {
      toast.error('Trace and span name are required');
      return;
    }
    try {
      const result = await api.tracingPipeline.startSpan(selectedTraceId, {
        name: spanForm.name.trim(),
        parent_span_id: spanForm.parent_span_id.trim() || null,
        kind: spanForm.kind,
        agent_id: spanForm.agent_id.trim() || undefined,
        resource: spanForm.resource.trim() || undefined,
      });
      const newId = result?.span_id ?? result?.id;
      toast.success(`Span started: ${newId ?? ''}`);
      setSpanForm({ name: '', parent_span_id: '', kind: 'internal', agent_id: '', resource: '' });
      await loadTraceDetail(selectedTraceId);
      if (newId) setSelectedSpanId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleEndSpan = async () => {
    if (!selectedSpanId) return;
    try {
      await api.tracingPipeline.endSpan(selectedSpanId, { status: 'ok' });
      toast.success('Span ended');
      loadSpanDetail(selectedSpanId);
      if (selectedTraceId) loadTraceDetail(selectedTraceId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEvent = async () => {
    if (!selectedSpanId || !eventForm.name.trim()) return;
    try {
      let payload: any = {};
      if (eventForm.payload.trim()) {
        try { payload = JSON.parse(eventForm.payload); } catch { payload = { text: eventForm.payload }; }
      }
      await api.tracingPipeline.addEvent(selectedSpanId, {
        name: eventForm.name.trim(),
        payload,
        level: eventForm.level,
      });
      toast.success('Event added to span');
      setEventForm({ name: '', level: 'info', payload: '' });
      loadSpanDetail(selectedSpanId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddAttribute = async () => {
    if (!selectedSpanId || !attrForm.key.trim()) return;
    try {
      let value: any = attrForm.value;
      // Try to coerce numeric or JSON values
      if (value.trim() !== '' && !isNaN(Number(value))) value = Number(value);
      else if (value === 'true') value = true;
      else if (value === 'false') value = false;
      else {
        try { value = JSON.parse(value); } catch { /* keep as string */ }
      }
      await api.tracingPipeline.addAttribute(selectedSpanId, attrForm.key.trim(), value);
      toast.success('Attribute updated');
      setAttrForm({ key: '', value: '' });
      loadSpanDetail(selectedSpanId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLinkSpans = async () => {
    if (!selectedSpanId || !linkForm.linked_trace_id.trim() || !linkForm.linked_span_id.trim()) return;
    try {
      await api.tracingPipeline.linkSpans(selectedSpanId, {
        linked_trace_id: linkForm.linked_trace_id.trim(),
        linked_span_id: linkForm.linked_span_id.trim(),
        relationship: linkForm.relationship,
      });
      toast.success('Span linked');
      setLinkForm({ linked_trace_id: '', linked_span_id: '', relationship: 'follows_from' });
      loadSpanDetail(selectedSpanId);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🔍 Tracing Pipeline</h2>
          <p className="panel-subtitle">Distributed trace observability with span-level context propagation</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading tracing pipeline...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🔍 Tracing Pipeline</h2>
        <p className="panel-subtitle">Distributed trace observability with span-level context propagation</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_traces ?? '-'}</span><span className="stat-label">Traces</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_traces ?? '-'}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_spans ?? '-'}</span><span className="stat-label">Spans</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_spans ?? '-'}</span><span className="stat-label">Open Spans</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.error_spans ?? '-'}</span><span className="stat-label">Errors</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'trace', 'span'] as const).map(s => (
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

      {/* Trace selector for trace/span sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Trace</label>
          <select
            value={selectedTraceId}
            onChange={e => { setSelectedTraceId(e.target.value); setSelectedSpanId(''); setSpanDetail(null); }}
          >
            <option value="">— Select a trace —</option>
            {traces.map((t: any) => {
              const id = t.trace_id ?? t.id;
              return <option key={id} value={id}>{t.root_span_name ?? id}</option>;
            })}
          </select>
        </div>
      )}

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Tracing Pipeline Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Traces</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_traces ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Traces</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_traces ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Spans</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_spans ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Error Spans</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.error_spans ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Span Duration (ms)</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{typeof stats.avg_span_duration_ms === 'number' ? stats.avg_span_duration_ms.toFixed(2) : (stats.avg_span_duration_ms ?? '-')}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Trace Duration (ms)</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{typeof stats.avg_trace_duration_ms === 'number' ? stats.avg_trace_duration_ms.toFixed(2) : (stats.avg_trace_duration_ms ?? '-')}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Traces</h3>
            <button onClick={loadTraces} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {traces.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No traces recorded yet. Start a new trace in the Trace section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {traces.slice(0, 10).map((t: any) => {
                  const id = t.trace_id ?? t.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{t.root_span_name ?? id}</div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id}</div>
                        </div>
                        <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setSelectedTraceId(id); setActiveSection('trace'); }}>View</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Trace Section */}
      {activeSection === 'trace' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Start New Trace</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Root Span Name *</label>
                <input value={traceForm.root_span_name} onChange={e => setTraceForm({ ...traceForm, root_span_name: e.target.value })} placeholder="e.g. handle_chat_request" />
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input value={traceForm.agent_id} onChange={e => setTraceForm({ ...traceForm, agent_id: e.target.value })} placeholder="optional" />
              </div>
              <div className="form-group">
                <label>Resource</label>
                <input value={traceForm.resource} onChange={e => setTraceForm({ ...traceForm, resource: e.target.value })} placeholder="e.g. chat-service" />
              </div>
            </div>
            <button onClick={handleStartTrace} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Start Trace</button>
          </div>

          {selectedTraceId && traceDetail && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h3 style={{ color: themeColors.text }}>Trace Detail: {selectedTraceId}</h3>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(traceDetail, null, 2)}</pre>
              {traceSummary && (
                <>
                  <h4 style={{ color: themeColors.text, marginTop: 16 }}>Critical Path Summary</h4>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(traceSummary, null, 2)}</pre>
                </>
              )}
            </div>
          )}

          {selectedTraceId && traceDetail?.spans && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginTop: 16 }}>
              <h3 style={{ color: themeColors.text }}>Spans in Trace</h3>
              <div style={{ display: 'grid', gap: 6, marginTop: 12 }}>
                {traceDetail.spans.map((sp: any) => {
                  const id = sp.span_id ?? sp.id;
                  return (
                    <div key={id} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{sp.name}</div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id} · {sp.kind ?? 'internal'} · {sp.status ?? '-'}</div>
                      </div>
                      <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setSelectedSpanId(id); setActiveSection('span'); }}>Inspect</button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Span Section */}
      {activeSection === 'span' && selectedTraceId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Start Child Span</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Span Name *</label>
                <input value={spanForm.name} onChange={e => setSpanForm({ ...spanForm, name: e.target.value })} placeholder="e.g. call_llm" />
              </div>
              <div className="form-group">
                <label>Parent Span ID</label>
                <input value={spanForm.parent_span_id} onChange={e => setSpanForm({ ...spanForm, parent_span_id: e.target.value })} placeholder="root if empty" />
              </div>
              <div className="form-group">
                <label>Kind</label>
                <select value={spanForm.kind} onChange={e => setSpanForm({ ...spanForm, kind: e.target.value })}>
                  {SPAN_KINDS.map(k => <option key={k} value={k}>{k}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input value={spanForm.agent_id} onChange={e => setSpanForm({ ...spanForm, agent_id: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Resource</label>
                <input value={spanForm.resource} onChange={e => setSpanForm({ ...spanForm, resource: e.target.value })} />
              </div>
            </div>
            <button onClick={handleStartSpan} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Start Span</button>
          </div>

          <div className="form-group" style={{ marginBottom: 16 }}>
            <label>Inspect Span</label>
            <select value={selectedSpanId} onChange={e => setSelectedSpanId(e.target.value)}>
              <option value="">— Select a span —</option>
              {(traceDetail?.spans ?? []).map((sp: any) => {
                const id = sp.span_id ?? sp.id;
                return <option key={id} value={id}>{sp.name} ({id})</option>;
              })}
            </select>
          </div>

          {selectedSpanId && spanDetail && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ color: themeColors.text }}>Span: {spanDetail.name}</h3>
                {spanDetail.end_time === null || spanDetail.end_time === undefined ? (
                  <button onClick={handleEndSpan} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>End Span</button>
                ) : (
                  <span style={{ color: themeColors.text, opacity: 0.7 }}>Closed</span>
                )}
              </div>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(spanDetail, null, 2)}</pre>
            </div>
          )}

          {selectedSpanId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Add Event</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Event Name *</label>
                    <input value={eventForm.name} onChange={e => setEventForm({ ...eventForm, name: e.target.value })} placeholder="e.g. cache_miss" />
                  </div>
                  <div className="form-group">
                    <label>Level</label>
                    <select value={eventForm.level} onChange={e => setEventForm({ ...eventForm, level: e.target.value })}>
                      {EVENT_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Payload (JSON or text)</label>
                    <textarea rows={3} value={eventForm.payload} onChange={e => setEventForm({ ...eventForm, payload: e.target.value })} placeholder='{"key":"value"}' />
                  </div>
                </div>
                <button onClick={handleAddEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Event</button>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Set Attribute</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, marginTop: 12, alignItems: 'flex-end' }}>
                  <div className="form-group">
                    <label>Key *</label>
                    <input value={attrForm.key} onChange={e => setAttrForm({ ...attrForm, key: e.target.value })} placeholder="e.g. user.id" />
                  </div>
                  <div className="form-group">
                    <label>Value</label>
                    <input value={attrForm.value} onChange={e => setAttrForm({ ...attrForm, value: e.target.value })} placeholder="string, number, bool, or JSON" />
                  </div>
                  <button onClick={handleAddAttribute} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Set</button>
                </div>
              </div>

              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <h3 style={{ color: themeColors.text }}>Link to Another Span</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Linked Trace ID *</label>
                    <input value={linkForm.linked_trace_id} onChange={e => setLinkForm({ ...linkForm, linked_trace_id: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Linked Span ID *</label>
                    <input value={linkForm.linked_span_id} onChange={e => setLinkForm({ ...linkForm, linked_span_id: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Relationship</label>
                    <select value={linkForm.relationship} onChange={e => setLinkForm({ ...linkForm, relationship: e.target.value })}>
                      <option value="follows_from">follows_from</option>
                      <option value="child_of">child_of</option>
                    </select>
                  </div>
                </div>
                <button onClick={handleLinkSpans} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Link Span</button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default TracingPipelinePanel;
