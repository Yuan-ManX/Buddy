import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Theme: amber for attention allocation
const themeColors = {
  primary: '#d97706',
  secondary: '#f59e0b',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

// Enum values must match backend AttentionMode / PriorityLevel / FocusType / DecayFunction exactly (lowercase).
const ATTENTION_MODES = ['focused', 'divided', 'scanning', 'deep_work', 'background'];
const PRIORITY_LEVELS = ['critical', 'high', 'medium', 'low', 'background'];
const FOCUS_TYPES = ['task', 'context', 'goal', 'conversation', 'monitoring', 'learning'];
const DECAY_FUNCTIONS = ['linear', 'exponential', 'logarithmic', 'step'];

export const AttentionAllocatorPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'budget' | 'allocate'>('overview');

  // Budgets / targets / allocations / snapshot
  const [budgets, setBudgets] = useState<any[]>([]);
  const [selectedBudgetId, setSelectedBudgetId] = useState<string>('');
  const [budgetDetail, setBudgetDetail] = useState<any>(null);
  const [targets, setTargets] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [snapshot, setSnapshot] = useState<any>(null);

  // Budget form
  const [budgetForm, setBudgetForm] = useState({
    agent_id: '',
    total_budget: '100',
    mode: 'focused',
    max_concurrent_targets: '5',
  });

  // Target form
  const [targetForm, setTargetForm] = useState({
    name: '',
    description: '',
    focus_type: 'task',
    priority: 'medium',
    base_weight: '1.0',
    urgency: '0.5',
    importance: '0.5',
    deadline: '',
    decay_function: 'linear',
    decay_rate: '0.1',
    metadata: '',
  });

  // Allocate form
  const [allocateForm, setAllocateForm] = useState({
    target_id: '',
    allocated_weight: '',
  });

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.attentionAllocator.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load attention allocator stats');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBudgets = useCallback(async () => {
    try {
      const result = await api.attentionAllocator.listBudgets();
      const list = Array.isArray(result) ? result : (result?.budgets ?? []);
      setBudgets(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load budgets');
    }
  }, [toast]);

  const loadBudgetDetail = useCallback(async (budgetId: string) => {
    if (!budgetId) return;
    try {
      const detail = await api.attentionAllocator.getBudget(budgetId);
      setBudgetDetail(detail);
    } catch (e: any) {
      setBudgetDetail(null);
    }
  }, []);

  const loadTargets = useCallback(async (budgetId: string) => {
    if (!budgetId) return;
    try {
      const result = await api.attentionAllocator.listTargets(budgetId);
      const list = Array.isArray(result) ? result : (result?.targets ?? []);
      setTargets(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load targets');
    }
  }, [toast]);

  const loadAllocations = useCallback(async (budgetId: string) => {
    if (!budgetId) return;
    try {
      const result = await api.attentionAllocator.getAllocations(budgetId);
      const list = Array.isArray(result) ? result : (result?.allocations ?? []);
      setAllocations(list);
    } catch (e: any) {
      toast.error(e.message || 'Failed to load allocations');
    }
  }, [toast]);

  const loadSnapshot = useCallback(async (budgetId: string) => {
    if (!budgetId) return;
    try {
      const s = await api.attentionAllocator.getSnapshot(budgetId);
      setSnapshot(s);
    } catch (e: any) {
      setSnapshot(null);
    }
  }, []);

  // Initial load
  useEffect(() => { loadStats(); }, [loadStats]);

  // Reload stats + budgets when entering overview
  useEffect(() => {
    if (activeSection === 'overview') {
      loadStats();
      loadBudgets();
    }
  }, [activeSection, loadStats, loadBudgets]);

  // When budget changes, refresh its detail, targets, allocations, snapshot
  useEffect(() => {
    if (selectedBudgetId) {
      loadBudgetDetail(selectedBudgetId);
      loadTargets(selectedBudgetId);
      loadAllocations(selectedBudgetId);
      loadSnapshot(selectedBudgetId);
    }
  }, [selectedBudgetId, loadBudgetDetail, loadTargets, loadAllocations, loadSnapshot]);

  // Auto-select first budget when entering non-overview sections
  useEffect(() => {
    if (activeSection !== 'overview' && !selectedBudgetId && budgets.length > 0) {
      setSelectedBudgetId(budgets[0].budget_id ?? budgets[0].id);
    }
  }, [activeSection, selectedBudgetId, budgets]);

  const handleCreateBudget = async () => {
    if (!budgetForm.agent_id.trim()) {
      toast.error('Agent ID is required');
      return;
    }
    try {
      const result = await api.attentionAllocator.createBudget({
        agent_id: budgetForm.agent_id.trim(),
        total_budget: Number(budgetForm.total_budget),
        mode: budgetForm.mode,
        max_concurrent_targets: Number(budgetForm.max_concurrent_targets),
      });
      toast.success('Budget created');
      setBudgetForm({ agent_id: '', total_budget: '100', mode: 'focused', max_concurrent_targets: '5' });
      await loadBudgets();
      const newId = result?.budget_id ?? result?.id;
      if (newId) setSelectedBudgetId(newId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRegisterTarget = async () => {
    if (!selectedBudgetId || !targetForm.name.trim()) {
      toast.error('Budget and target name are required');
      return;
    }
    try {
      const payload: any = {
        name: targetForm.name.trim(),
        description: targetForm.description.trim() || undefined,
        focus_type: targetForm.focus_type,
        priority: targetForm.priority,
        base_weight: Number(targetForm.base_weight),
        urgency: Number(targetForm.urgency),
        importance: Number(targetForm.importance),
        decay_function: targetForm.decay_function,
        decay_rate: Number(targetForm.decay_rate),
      };
      if (targetForm.deadline.trim() !== '') payload.deadline = Number(targetForm.deadline);
      if (targetForm.metadata.trim()) {
        try { payload.metadata = JSON.parse(targetForm.metadata); } catch { payload.metadata = { text: targetForm.metadata }; }
      }
      await api.attentionAllocator.registerTarget(selectedBudgetId, payload);
      toast.success('Target registered');
      setTargetForm({ name: '', description: '', focus_type: 'task', priority: 'medium', base_weight: '1.0', urgency: '0.5', importance: '0.5', deadline: '', decay_function: 'linear', decay_rate: '0.1', metadata: '' });
      loadTargets(selectedBudgetId);
      loadSnapshot(selectedBudgetId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAllocate = async () => {
    if (!selectedBudgetId || !allocateForm.target_id.trim()) {
      toast.error('Budget and target ID are required');
      return;
    }
    try {
      const payload: any = { target_id: allocateForm.target_id.trim() };
      if (allocateForm.allocated_weight.trim() !== '') payload.allocated_weight = Number(allocateForm.allocated_weight);
      await api.attentionAllocator.allocate(selectedBudgetId, payload);
      toast.success('Attention allocated');
      setAllocateForm({ target_id: '', allocated_weight: '' });
      loadAllocations(selectedBudgetId);
      loadSnapshot(selectedBudgetId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeallocate = async (targetId: string) => {
    if (!selectedBudgetId) return;
    try {
      await api.attentionAllocator.deallocate(selectedBudgetId, targetId);
      toast.success('Attention deallocated');
      loadAllocations(selectedBudgetId);
      loadSnapshot(selectedBudgetId);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRebalance = async () => {
    if (!selectedBudgetId) return;
    try {
      const result = await api.attentionAllocator.rebalance(selectedBudgetId);
      setSnapshot(result);
      toast.success('Budget rebalanced');
      loadAllocations(selectedBudgetId);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🎯 Attention Allocator</h2>
          <p className="panel-subtitle">Allocate attention budgets across competing targets</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading attention allocator...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🎯 Attention Allocator</h2>
        <p className="panel-subtitle">Allocate attention budgets across competing targets</p>
        {error && <div className="error-banner">{error}<button onClick={loadStats} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_budgets ?? '-'}</span><span className="stat-label">Budgets</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_targets ?? '-'}</span><span className="stat-label">Targets</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_allocations ?? '-'}</span><span className="stat-label">Allocations</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_targets ?? '-'}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.rebalance_count ?? '-'}</span><span className="stat-label">Rebalances</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'budget', 'allocate'] as const).map(s => (
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

      {/* Budget selector shared across non-overview sections */}
      {activeSection !== 'overview' && (
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>Active Budget</label>
          <select
            value={selectedBudgetId}
            onChange={e => { setSelectedBudgetId(e.target.value); setSnapshot(null); setTargets([]); setAllocations([]); }}
          >
            <option value="">— Select a budget —</option>
            {budgets.map((b: any) => {
              const id = b.budget_id ?? b.id;
              return <option key={id} value={id}>{b.agent_id ?? id}</option>;
            })}
          </select>
        </div>
      )}

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Attention Allocator Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Budgets</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_budgets ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Targets</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_targets ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Allocations</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.total_allocations ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Targets</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.active_targets ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Rebalances</div>
                <div style={{ fontSize: 24, color: themeColors.primary }}>{stats.rebalance_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Recent Budgets</h3>
            <button onClick={() => loadBudgets()} className="btn-sm" style={{ marginBottom: 12, background: themeColors.primary, color: '#fff' }}>Refresh</button>
            {budgets.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7 }}>No budgets recorded. Create one in the Budget section.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {budgets.slice(0, 10).map((b: any) => {
                  const id = b.budget_id ?? b.id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, color: themeColors.text }}>{b.agent_id ?? 'unknown'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{b.mode ?? 'unknown'}]</span></div>
                          <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>budget: {b.total_budget ?? '-'} · {id}</div>
                        </div>
                        <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }} onClick={() => { setActiveSection('budget'); setSelectedBudgetId(id); }}>Open</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Budget Section */}
      {activeSection === 'budget' && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Create Budget</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
              <div className="form-group">
                <label>Agent ID *</label>
                <input value={budgetForm.agent_id} onChange={e => setBudgetForm({ ...budgetForm, agent_id: e.target.value })} placeholder="e.g. agent_x1" />
              </div>
              <div className="form-group">
                <label>Total Budget</label>
                <input value={budgetForm.total_budget} onChange={e => setBudgetForm({ ...budgetForm, total_budget: e.target.value })} type="number" />
              </div>
              <div className="form-group">
                <label>Mode</label>
                <select value={budgetForm.mode} onChange={e => setBudgetForm({ ...budgetForm, mode: e.target.value })}>
                  {ATTENTION_MODES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Max Concurrent Targets</label>
                <input value={budgetForm.max_concurrent_targets} onChange={e => setBudgetForm({ ...budgetForm, max_concurrent_targets: e.target.value })} type="number" />
              </div>
            </div>
            <button onClick={handleCreateBudget} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Create Budget</button>
          </div>

          {selectedBudgetId && (
            <>
              <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
                <h3 style={{ color: themeColors.text }}>Register Target</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input value={targetForm.name} onChange={e => setTargetForm({ ...targetForm, name: e.target.value })} placeholder="e.g. handle_customer_query" />
                  </div>
                  <div className="form-group">
                    <label>Focus Type</label>
                    <select value={targetForm.focus_type} onChange={e => setTargetForm({ ...targetForm, focus_type: e.target.value })}>
                      {FOCUS_TYPES.map(f => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Priority</label>
                    <select value={targetForm.priority} onChange={e => setTargetForm({ ...targetForm, priority: e.target.value })}>
                      {PRIORITY_LEVELS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Base Weight</label>
                    <input value={targetForm.base_weight} onChange={e => setTargetForm({ ...targetForm, base_weight: e.target.value })} type="number" step="0.1" />
                  </div>
                  <div className="form-group">
                    <label>Urgency (0-1)</label>
                    <input value={targetForm.urgency} onChange={e => setTargetForm({ ...targetForm, urgency: e.target.value })} type="number" min="0" max="1" step="0.1" />
                  </div>
                  <div className="form-group">
                    <label>Importance (0-1)</label>
                    <input value={targetForm.importance} onChange={e => setTargetForm({ ...targetForm, importance: e.target.value })} type="number" min="0" max="1" step="0.1" />
                  </div>
                  <div className="form-group">
                    <label>Deadline (epoch)</label>
                    <input value={targetForm.deadline} onChange={e => setTargetForm({ ...targetForm, deadline: e.target.value })} type="number" />
                  </div>
                  <div className="form-group">
                    <label>Decay Function</label>
                    <select value={targetForm.decay_function} onChange={e => setTargetForm({ ...targetForm, decay_function: e.target.value })}>
                      {DECAY_FUNCTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Decay Rate</label>
                    <input value={targetForm.decay_rate} onChange={e => setTargetForm({ ...targetForm, decay_rate: e.target.value })} type="number" step="0.01" />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Description</label>
                    <input value={targetForm.description} onChange={e => setTargetForm({ ...targetForm, description: e.target.value })} />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Metadata (JSON)</label>
                    <input value={targetForm.metadata} onChange={e => setTargetForm({ ...targetForm, metadata: e.target.value })} placeholder='{"channel":"slack"}' />
                  </div>
                </div>
                <button onClick={handleRegisterTarget} className="btn-primary" style={{ marginTop: 12, background: themeColors.primary, color: '#fff' }}>Register Target</button>
              </div>

              {budgetDetail && (
                <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                  <h3 style={{ color: themeColors.text }}>Budget: {selectedBudgetId}</h3>
                  <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 300, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(budgetDetail, null, 2)}</pre>
                  <h4 style={{ color: themeColors.text, marginTop: 12 }}>Targets ({targets.length})</h4>
                  {targets.length === 0 ? (
                    <div style={{ color: themeColors.text, opacity: 0.7 }}>No targets registered for this budget.</div>
                  ) : (
                    <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                      {targets.map((t: any, i: number) => {
                        const id = t.target_id ?? t.id ?? i;
                        return (
                          <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}` }}>
                            <div style={{ fontWeight: 600, color: themeColors.text }}>{t.name ?? 'target'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>[{t.focus_type ?? 'task'} · {t.priority ?? 'medium'}]</span></div>
                            <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>weight {t.base_weight} · urgency {t.urgency} · importance {t.importance} · {id}</div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Allocate Section */}
      {activeSection === 'allocate' && selectedBudgetId && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Allocate Attention</h3>
            <div style={{ display: 'flex', gap: 12, marginTop: 12, alignItems: 'flex-end' }}>
              <div className="form-group" style={{ flex: '1 1 auto' }}>
                <label>Target ID *</label>
                <input value={allocateForm.target_id} onChange={e => setAllocateForm({ ...allocateForm, target_id: e.target.value })} placeholder="e.g. tgt_xxx" list="target-options" />
                <datalist id="target-options">
                  {targets.map((t: any) => <option key={t.target_id ?? t.id} value={t.target_id ?? t.id} />)}
                </datalist>
              </div>
              <div className="form-group" style={{ flex: '0 0 200px' }}>
                <label>Allocated Weight</label>
                <input value={allocateForm.allocated_weight} onChange={e => setAllocateForm({ ...allocateForm, allocated_weight: e.target.value })} type="number" placeholder="auto if empty" />
              </div>
              <button onClick={handleAllocate} className="btn-primary" style={{ background: themeColors.primary, color: '#fff' }}>Allocate</button>
            </div>
          </div>

          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Allocations ({allocations.length})</h3>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button onClick={() => loadAllocations(selectedBudgetId)} className="btn-sm" style={{ background: themeColors.primary, color: '#fff' }}>Refresh</button>
              <button onClick={handleRebalance} className="btn-sm" style={{ background: themeColors.secondary, color: '#fff' }}>Rebalance</button>
            </div>
            {allocations.length === 0 ? (
              <div style={{ color: themeColors.text, opacity: 0.7, marginTop: 8 }}>No allocations recorded.</div>
            ) : (
              <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                {allocations.map((a: any, i: number) => {
                  const id = a.allocation_id ?? a.id ?? i;
                  const targetId = a.target_id ?? a.target?.target_id;
                  return (
                    <div key={id} style={{ padding: 10, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}`, borderLeft: `4px solid ${themeColors.primary}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, color: themeColors.text }}>{a.target_name ?? targetId ?? 'target'} <span style={{ color: themeColors.primary, fontSize: 12, marginLeft: 6 }}>weight {a.allocated_weight ?? '-'}</span></div>
                        <div style={{ fontSize: 12, color: themeColors.text, opacity: 0.7 }}>{a.status ?? 'active'} · {id}</div>
                      </div>
                      <button className="btn-sm" style={{ background: '#ef4444', color: '#fff' }} onClick={() => handleDeallocate(targetId)}>Deallocate</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {snapshot && (
            <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h3 style={{ color: themeColors.text }}>Budget Snapshot</h3>
              <pre style={{ background: '#fff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 400, border: `1px solid ${themeColors.border}`, fontSize: 12 }}>{JSON.stringify(snapshot, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AttentionAllocatorPanel;
