import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: purple/violet for temporal reasoning
const themeColors = {
  primary: '#8b5cf6',
  secondary: '#a78bfa',
  bg: '#f5f3ff',
  border: '#ddd6fe',
  accent: '#ede9fe',
  text: '#4c1d95',
};

// Enum values must match backend EventStatus / TemporalConstraintType exactly (lowercase).
const EVENT_STATUSES = ['scheduled', 'in_progress', 'completed', 'cancelled', 'delayed', 'missed'];
const CONSTRAINT_TYPES = ['deadline', 'duration', 'ordering', 'separation', 'recurrence'];
const TEMPORAL_RELATIONS = [
  'before', 'after', 'meets', 'met_by', 'overlaps', 'overlapped_by',
  'during', 'contains', 'starts', 'started_by', 'finishes', 'finished_by', 'equals',
];

export const TemporalEnginePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'plan' | 'event' | 'constraint'>('overview');

  // Plans / events / constraints
  const [plans, setPlans] = useState<any[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>('');
  const [events, setEvents] = useState<any[]>([]);
  const [constraints, setConstraints] = useState<any[]>([]);
  const [consistency, setConsistency] = useState<any>(null);
  const [order, setOrder] = useState<any>(null);
  const [conflicts, setConflicts] = useState<any>(null);
  const [criticalPath, setCriticalPath] = useState<any>(null);
  const [deadlines, setDeadlines] = useState<any>(null);

  // Plan form
  const [planForm, setPlanForm] = useState({ name: '', description: '' });

  // Event form
  const [eventForm, setEventForm] = useState({
    name: '',
    description: '',
    start: '',
    end: '',
    duration: '',
    priority: '2',
    agent_id: '',
    tags: '',
  });

  // Constraint form
  const [constraintForm, setConstraintForm] = useState({
    event_id: '',
    constraint_type: 'ordering',
    relation: '',
    target_event_id: '',
    min_value: '',
    max_value: '',
    deadline: '',
    description: '',
  });

  // Allen relation form
  const [relationForm, setRelationForm] = useState({
    start_a: '0',
    end_a: '10',
    start_b: '5',
    end_b: '15',
  });
  const [relationResult, setRelationResult] = useState<string>('');

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.temporalEngine.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load temporal engine stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPlans = useCallback(async () => {
    try {
      const result = await api.temporalEngine.listPlans();
      const list = Array.isArray(result) ? result : (result?.plans ?? []);
      setPlans(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load plans');
    }
  }, [toast]);

  const loadEvents = useCallback(async (planId: string) => {
    if (!planId) return;
    try {
      const result = await api.temporalEngine.listEvents(planId);
      const list = Array.isArray(result) ? result : (result?.events ?? []);
      setEvents(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load events');
    }
  }, [toast]);

  const loadConstraints = useCallback(async (planId: string) => {
    if (!planId) return;
    try {
      const result = await api.temporalEngine.listConstraints(planId);
      const list = Array.isArray(result) ? result : (result?.constraints ?? []);
      setConstraints(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load constraints');
    }
  }, [toast]);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + plans when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadPlans();
    }
  }, [activeSection, loadStats, loadPlans]);

  // When plan changes, refresh its events / constraints
  useEffect(() => {
    if (selectedPlanId) {
      loadEvents(selectedPlanId);
      loadConstraints(selectedPlanId);
    }
  }, [selectedPlanId, loadEvents, loadConstraints]);

  // Auto-select first plan when entering non-overview sections
  useEffect(() => {
    if (activeSection !== 'overview' && !selectedPlanId && plans.length > 0) {
      setSelectedPlanId(plans[0].plan_id ?? plans[0].id);
    }
  }, [activeSection, selectedPlanId, plans]);

  const handleCreatePlan = async () => {
    if (!planForm.name.trim()) {
      toast.error('Plan name is required');
      return;
    }
    try {
      const result = await api.temporalEngine.createPlan({
        name: planForm.name.trim(),
        description: planForm.description.trim() || undefined,
      });
      const newId = result?.plan_id ?? result?.id;
      toast.success(`Plan created: ${newId ?? ''}`);
      setPlanForm({ name: '', description: '' });
      await loadPlans();
      if (newId) setSelectedPlanId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddEvent = async () => {
    if (!selectedPlanId || !eventForm.name.trim()) {
      toast.error('Plan and event name are required');
      return;
    }
    try {
      const tags = eventForm.tags.split(',').map(s => s.trim()).filter(Boolean);
      await api.temporalEngine.addEvent(selectedPlanId, {
        name: eventForm.name.trim(),
        description: eventForm.description.trim() || undefined,
        start: eventForm.start.trim() !== '' ? Number(eventForm.start) : null,
        end: eventForm.end.trim() !== '' ? Number(eventForm.end) : null,
        duration: eventForm.duration.trim() !== '' ? Number(eventForm.duration) : null,
        priority: Number(eventForm.priority),
        agent_id: eventForm.agent_id.trim() || undefined,
        tags,
        metadata: {},
      });
      toast.success('Event added');
      setEventForm({ name: '', description: '', start: '', end: '', duration: '', priority: '2', agent_id: '', tags: '' });
      loadEvents(selectedPlanId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleUpdateEventStatus = async (eventId: string, status: string) => {
    if (!selectedPlanId) return;
    try {
      await api.temporalEngine.updateEventStatus(selectedPlanId, eventId, status);
      toast.success(`Event marked ${status}`);
      loadEvents(selectedPlanId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddConstraint = async () => {
    if (!selectedPlanId) {
      toast.error('Select a plan first');
      return;
    }
    try {
      await api.temporalEngine.addConstraint(selectedPlanId, {
        event_id: constraintForm.event_id.trim() || null,
        constraint_type: constraintForm.constraint_type,
        relation: constraintForm.relation || null,
        target_event_id: constraintForm.target_event_id.trim() || null,
        min_value: constraintForm.min_value.trim() !== '' ? Number(constraintForm.min_value) : null,
        max_value: constraintForm.max_value.trim() !== '' ? Number(constraintForm.max_value) : null,
        deadline: constraintForm.deadline.trim() !== '' ? Number(constraintForm.deadline) : null,
        description: constraintForm.description.trim() || undefined,
      });
      toast.success('Constraint added');
      setConstraintForm({ event_id: '', constraint_type: 'ordering', relation: '', target_event_id: '', min_value: '', max_value: '', deadline: '', description: '' });
      loadConstraints(selectedPlanId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCheckConsistency = async () => {
    if (!selectedPlanId) return;
    try {
      const r = await api.temporalEngine.checkConsistency(selectedPlanId);
      setConsistency(r);
      toast.success('Consistency check complete');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetOrder = async () => {
    if (!selectedPlanId) return;
    try {
      const r = await api.temporalEngine.getOrder(selectedPlanId);
      setOrder(r);
      toast.success('Order computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFindConflicts = async () => {
    if (!selectedPlanId) return;
    try {
      const r = await api.temporalEngine.findConflicts(selectedPlanId);
      setConflicts(r);
      toast.success('Conflicts scanned');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetCriticalPath = async () => {
    if (!selectedPlanId) return;
    try {
      const r = await api.temporalEngine.getCriticalPath(selectedPlanId);
      setCriticalPath(r);
      toast.success('Critical path computed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCheckDeadlines = async () => {
    if (!selectedPlanId) return;
    try {
      const r = await api.temporalEngine.checkDeadlines(selectedPlanId, Math.floor(Date.now() / 1000));
      setDeadlines(r);
      toast.success('Deadlines checked');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleComputeRelation = async () => {
    try {
      const r = await api.temporalEngine.computeRelation({
        start_a: Number(relationForm.start_a),
        end_a: relationForm.end_a.trim() !== '' ? Number(relationForm.end_a) : null,
        start_b: Number(relationForm.start_b),
        end_b: relationForm.end_b.trim() !== '' ? Number(relationForm.end_b) : null,
      });
      setRelationResult(r?.relation ?? '-');
      toast.success(`Relation: ${r?.relation ?? '-'}`);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>⏳ Temporal Engine</h2>
          <p className="panel-subtitle">Allen interval algebra, scheduling, and deadline management</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading temporal engine...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⏳ Temporal Engine</h2>
        <p className="panel-subtitle">Allen interval algebra, scheduling, and deadline management</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_plans ?? '-'}</span><span className="stat-label">Plans</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_events ?? '-'}</span><span className="stat-label">Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_constraints ?? '-'}</span><span className="stat-label">Constraints</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.consistency_issues ?? '-'}</span><span className="stat-label">Issues</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.missed_deadlines ?? '-'}</span><span className="stat-label">Missed Deadlines</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'plan', 'event', 'constraint'] as const).map(s => (
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

      {/* Plan selector shared across non-overview sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Plan</label>
          <select
            value={selectedPlanId}
            onChange={e => { setSelectedPlanId(e.target.value); setConsistency(null); setOrder(null); setConflicts(null); setCriticalPath(null); setDeadlines(null); }}
          >
            <option value="">— Select a plan —</option>
            {plans.map((p: any) => {
              const id = p.plan_id ?? p.id;
              return <option key={id} value={id}>{p.name ?? id}</option>;
            })}
          </select>
        </div>
      )}

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Temporal Engine Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Plans</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_plans ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_events ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Constraints</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_constraints ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Events</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_events ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Consistency Issues</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.consistency_issues ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Missed Deadlines</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.missed_deadlines ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Temporal Plans</h3>
            <button onClick={loadPlans} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {plans.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No plans yet. Create one in the Plan section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {plans.map((p: any) => {
                  const id = p.plan_id ?? p.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{p.name}</div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id} · {p.event_count ?? 0} events · {p.constraint_count ?? 0} constraints</div>
                      </div>
                      <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setSelectedPlanId(id); setActiveSection('event'); }}>Open</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Plan Section */}
      {activeSection === 'plan' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Temporal Plan</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={planForm.name} onChange={e => setPlanForm({ ...planForm, name: e.target.value })} placeholder="e.g. release_v1" />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input value={planForm.description} onChange={e => setPlanForm({ ...planForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleCreatePlan} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Plan</button>
          </div>

          {selectedPlanId && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h3 style={{ color: themeColors.text }}>Plan Analysis</h3>
              <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                <button onClick={handleCheckConsistency} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Check Consistency</button>
                <button onClick={handleGetOrder} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Topological Order</button>
                <button onClick={handleFindConflicts} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Find Conflicts</button>
                <button onClick={handleGetCriticalPath} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Critical Path</button>
                <button onClick={handleCheckDeadlines} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Check Deadlines</button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                {consistency && (
                  <div>
                    <h4 style={{ color: themeColors.text }}>Consistency</h4>
                    <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(consistency, null, 2)}</pre>
                  </div>
                )}
                {order && (
                  <div>
                    <h4 style={{ color: themeColors.text }}>Topological Order</h4>
                    <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(order, null, 2)}</pre>
                  </div>
                )}
                {conflicts && (
                  <div>
                    <h4 style={{ color: themeColors.text }}>Conflicts</h4>
                    <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(conflicts, null, 2)}</pre>
                  </div>
                )}
                {criticalPath && (
                  <div>
                    <h4 style={{ color: themeColors.text }}>Critical Path</h4>
                    <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(criticalPath, null, 2)}</pre>
                  </div>
                )}
                {deadlines && (
                  <div>
                    <h4 style={{ color: themeColors.text }}>Deadlines</h4>
                    <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(deadlines, null, 2)}</pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Event Section */}
      {activeSection === 'event' && selectedPlanId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Event</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Name *</label>
                <input value={eventForm.name} onChange={e => setEventForm({ ...eventForm, name: e.target.value })} placeholder="e.g. design_review" />
              </div>
              <div className="form-group">
                <label>Start (unix)</label>
                <input value={eventForm.start} onChange={e => setEventForm({ ...eventForm, start: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>End (unix)</label>
                <input value={eventForm.end} onChange={e => setEventForm({ ...eventForm, end: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Duration (s)</label>
                <input value={eventForm.duration} onChange={e => setEventForm({ ...eventForm, duration: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Priority (0-5)</label>
                <input value={eventForm.priority} onChange={e => setEventForm({ ...eventForm, priority: e.target.value })} type="number" min="0" max="5" />
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input value={eventForm.agent_id} onChange={e => setEventForm({ ...eventForm, agent_id: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input value={eventForm.tags} onChange={e => setEventForm({ ...eventForm, tags: e.target.value })} placeholder="urgent,release" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={eventForm.description} onChange={e => setEventForm({ ...eventForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleAddEvent} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Event</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Events ({events.length})</h3>
            <button onClick={() => loadEvents(selectedPlanId)} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {events.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No events yet.</div>
            ) : (
              <div style={{ display: 'grid', gap: 6 }}>
                {events.map((ev: any) => {
                  const id = ev.event_id ?? ev.id;
                  return (
                    <div key={id} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{ev.name} <span style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>· P{ev.priority}</span></div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{id} · start {String(ev.interval?.start ?? ev.start ?? '-')} · end {String(ev.interval?.end ?? ev.end ?? '-')}</div>
                      </div>
                      <select
                        value={ev.status ?? 'scheduled'}
                        onChange={e => handleUpdateEventStatus(id, e.target.value)}
                        style={{ padding: '4px 8px', borderRadius: 4, border: `1px solid ${themeColors.border}` }}
                      >
                        {EVENT_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Constraint Section */}
      {activeSection === 'constraint' && selectedPlanId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Add Constraint</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Event</label>
                <select value={constraintForm.event_id} onChange={e => setConstraintForm({ ...constraintForm, event_id: e.target.value })}>
                  <option value="">— optional —</option>
                  {events.map((ev: any) => {
                    const id = ev.event_id ?? ev.id;
                    return <option key={id} value={id}>{ev.name}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Constraint Type</label>
                <select value={constraintForm.constraint_type} onChange={e => setConstraintForm({ ...constraintForm, constraint_type: e.target.value })}>
                  {CONSTRAINT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Relation</label>
                <select value={constraintForm.relation} onChange={e => setConstraintForm({ ...constraintForm, relation: e.target.value })}>
                  <option value="">— none —</option>
                  {TEMPORAL_RELATIONS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Event</label>
                <select value={constraintForm.target_event_id} onChange={e => setConstraintForm({ ...constraintForm, target_event_id: e.target.value })}>
                  <option value="">— optional —</option>
                  {events.map((ev: any) => {
                    const id = ev.event_id ?? ev.id;
                    return <option key={id} value={id}>{ev.name}</option>;
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Min Value</label>
                <input value={constraintForm.min_value} onChange={e => setConstraintForm({ ...constraintForm, min_value: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Max Value</label>
                <input value={constraintForm.max_value} onChange={e => setConstraintForm({ ...constraintForm, max_value: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Deadline (unix)</label>
                <input value={constraintForm.deadline} onChange={e => setConstraintForm({ ...constraintForm, deadline: e.target.value })} type="number" />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Description</label>
                <input value={constraintForm.description} onChange={e => setConstraintForm({ ...constraintForm, description: e.target.value })} />
              </div>
            </div>
            <button onClick={handleAddConstraint} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Add Constraint</button>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Constraints ({constraints.length})</h3>
            <button onClick={() => loadConstraints(selectedPlanId)} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {constraints.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No constraints yet.</div>
            ) : (
              <div style={{ display: 'grid', gap: 6 }}>
                {constraints.map((c: any) => {
                  const id = c.constraint_id ?? c.id;
                  return (
                    <div key={id} style={{ padding: 8, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                      <div style={{ fontWeight: 600, color: themeColors.text }}>{c.constraint_type} {c.relation ? `· ${c.relation}` : ''}</div>
                      <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>
                        {id} · event {c.event_id ?? '-'} · target {c.target_event_id ?? '-'}
                        {c.min_value !== null && c.min_value !== undefined ? ` · min ${c.min_value}` : ''}
                        {c.max_value !== null && c.max_value !== undefined ? ` · max ${c.max_value}` : ''}
                        {c.deadline !== null && c.deadline !== undefined ? ` · deadline ${c.deadline}` : ''}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Allen's Interval Algebra</h3>
            <p style={{ color: themeColors.text, opacity: 0.8, marginTop: 4 }}>Compute the temporal relation between two intervals A and B.</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Start A</label>
                <input value={relationForm.start_a} onChange={e => setRelationForm({ ...relationForm, start_a: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>End A</label>
                <input value={relationForm.end_a} onChange={e => setRelationForm({ ...relationForm, end_a: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Start B</label>
                <input value={relationForm.start_b} onChange={e => setRelationForm({ ...relationForm, start_b: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>End B</label>
                <input value={relationForm.end_b} onChange={e => setRelationForm({ ...relationForm, end_b: e.target.value })} type="number" />
              </div>
            </div>
            <button onClick={handleComputeRelation} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Compute Relation</button>
            {relationResult && (
              <div style={{ marginTop: 16, padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Relation: <span style={{ color: themeColors.primary }}>{relationResult}</span></div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TemporalEnginePanel;
