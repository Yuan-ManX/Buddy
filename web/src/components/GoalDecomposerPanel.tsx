import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { GoalDecomposerStats, GoalTree, DecomposeResult, SubGoalInfo } from '../types';

export const GoalDecomposerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<GoalDecomposerStats | null>(null);
  const [trees, setTrees] = useState<GoalTree[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'decompose' | 'trees' | 'detail'>('overview');
  const [decomposeForm, setDecomposeForm] = useState({
    description: '', strategy: 'dependency_first', tags: '',
  });
  const [selectedTree, setSelectedTree] = useState<GoalTree | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, t] = await Promise.all([
        api.goalDecomposer.stats(),
        api.goalDecomposer.trees(),
      ]);
      setStats(s);
      setTrees(t.trees);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load goal decomposer data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleDecompose = async () => {
    if (!decomposeForm.description.trim()) return;
    try {
      const result = await api.goalDecomposer.decompose({
        description: decomposeForm.description,
        strategy: decomposeForm.strategy,
        tags: decomposeForm.tags ? decomposeForm.tags.split(',').map(s => s.trim()) : undefined,
      });
      toast.success(`Goal decomposed: ${result.sub_goals} sub-goals`);
      setDecomposeForm({ description: '', strategy: 'dependency_first', tags: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleViewTree = async (goalId: string) => {
    try {
      setTreeLoading(true);
      const tree = await api.goalDecomposer.tree(goalId);
      setSelectedTree(tree);
      setActiveSection('detail');
    } catch (e: any) { toast.error(e.message); }
    finally { setTreeLoading(false); }
  };

  const handleNextLayer = async (goalId: string) => {
    try {
      await api.goalDecomposer.nextLayer(goalId);
      toast.success('Next layer generated');
      const updatedTree = await api.goalDecomposer.tree(goalId);
      setSelectedTree(updatedTree);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const strategyColors: Record<string, string> = {
    dependency_first: '#4f6ef7',
    breadth_first: '#22c55e',
    depth_first: '#f59e0b',
    parallel_optimal: '#8b5cf6',
    cost_aware: '#ef4444',
  };

  const statusColors: Record<string, string> = {
    completed: '#22c55e',
    in_progress: '#3b82f6',
    pending: '#9ca3af',
    failed: '#ef4444',
  };

  const statusLabels: Record<string, string> = {
    completed: 'Completed',
    in_progress: 'In Progress',
    pending: 'Pending',
    failed: 'Failed',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Goal Decomposer</h2>
          <p className="panel-subtitle">Break down complex goals into executable sub-goals</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading goal decomposer data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Goal Decomposer</h2>
        <p className="panel-subtitle">Break down complex goals into ordered, executable sub-goals with dependency tracking</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_decompositions}</span><span className="stat-label">Total Decompositions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.active_trees}</span><span className="stat-label">Active Trees</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.completed_trees}</span><span className="stat-label">Completed</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.failed_trees}</span><span className="stat-label">Failed</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'decompose', 'trees', 'detail'] as const).map(s => (
          <button key={s} className={`forge-tab ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>
            {s === 'detail' ? 'Tree Detail' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Strategy Distribution</h3>
          {Object.entries(stats.by_strategy).length > 0 ? (
            Object.entries(stats.by_strategy).map(([strategy, count]) => (
              <div key={strategy} className="dashboard-stat-row">
                <span style={{ color: strategyColors[strategy] || '#666', fontWeight: 600, textTransform: 'capitalize' }}>
                  {strategy.replace(/_/g, ' ')}
                </span>
                <strong>{count}</strong>
              </div>
            ))
          ) : (
            <div className="panel-empty">No strategy data yet</div>
          )}

          <h3 style={{ marginTop: 20 }}>Goal Trees Summary</h3>
          {trees.length === 0 ? (
            <div className="panel-empty">No goal trees created yet. Go to the Decompose tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {trees.map(tree => (
                <div key={tree.goal_id} className="forge-skill-card" style={{ cursor: 'pointer' }} onClick={() => handleViewTree(tree.goal_id)}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{tree.description}</div>
                    <span className="dashboard-badge" style={{ background: strategyColors[tree.strategy] || '#666', color: '#fff' }}>
                      {tree.strategy.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Sub-Goals: {tree.sub_goals.length} | Tags: {tree.tags.join(', ') || 'none'}</div>
                    <div>Progress: {tree.progress.completed}/{tree.progress.total} ({tree.progress.percentage.toFixed(0)}%)</div>
                    <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 4, height: 8 }}>
                      <div style={{
                        width: `${tree.progress.percentage}%`,
                        background: `linear-gradient(90deg, #ef4444, #f59e0b, #22c55e)`,
                        height: '100%',
                        borderRadius: 4,
                      }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Decompose */}
      {activeSection === 'decompose' && (
        <div className="dashboard-section">
          <h3>Create New Goal Decomposition</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Goal Description</label>
              <textarea
                rows={4}
                value={decomposeForm.description}
                onChange={e => setDecomposeForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the goal you want to decompose, e.g., 'Build a full-stack e-commerce platform'"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Strategy</label>
                <select value={decomposeForm.strategy} onChange={e => setDecomposeForm(f => ({ ...f, strategy: e.target.value }))}>
                  {['dependency_first', 'breadth_first', 'depth_first', 'parallel_optimal', 'cost_aware'].map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ flex: 2 }}>
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={decomposeForm.tags}
                  onChange={e => setDecomposeForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="frontend, backend, database"
                />
              </div>
            </div>
            <button className="btn-primary" onClick={handleDecompose}>Decompose Goal</button>
          </div>

          {stats && (
            <div style={{ marginTop: 20 }}>
              <h3>Strategy Guide</h3>
              <div className="forge-skill-list">
                {[
                  { name: 'dependency_first', desc: 'Order sub-goals by dependencies first, then execute' },
                  { name: 'breadth_first', desc: 'Explore all sub-goals at the same level before going deeper' },
                  { name: 'depth_first', desc: 'Follow each sub-goal chain to completion before moving on' },
                  { name: 'parallel_optimal', desc: 'Maximize parallel execution of independent sub-goals' },
                  { name: 'cost_aware', desc: 'Prioritize sub-goals by estimated cost efficiency' },
                ].map(s => (
                  <div key={s.name} className="forge-skill-card" style={{ marginBottom: 8 }}>
                    <div className="forge-skill-header">
                      <div className="forge-skill-name" style={{ color: strategyColors[s.name] }}>{s.name.replace(/_/g, ' ')}</div>
                    </div>
                    <div className="forge-skill-meta">
                      <div>{s.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Trees */}
      {activeSection === 'trees' && (
        <div className="dashboard-section">
          <h3>Goal Trees ({trees.length})</h3>
          {trees.length === 0 ? (
            <div className="panel-empty">No goal trees yet. Go to the Decompose tab to create one.</div>
          ) : (
            <div className="forge-skill-list">
              {trees.map(tree => (
                <div key={tree.goal_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{tree.description}</div>
                    <span className="dashboard-badge" style={{ background: strategyColors[tree.strategy] || '#666', color: '#fff' }}>
                      {tree.strategy.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Sub-Goals: {tree.sub_goals.length} | Tags: {tree.tags.join(', ') || 'none'}</div>
                    <div>Created: {new Date(tree.created_at).toLocaleString()} | Updated: {new Date(tree.updated_at).toLocaleString()}</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <span style={{ fontSize: '0.8rem', padding: '2px 6px', borderRadius: 4, background: '#e8f5e9', color: '#22c55e' }}>
                        Completed: {tree.progress.completed}
                      </span>
                      <span style={{ fontSize: '0.8rem', padding: '2px 6px', borderRadius: 4, background: '#e3f2fd', color: '#3b82f6' }}>
                        In Progress: {tree.progress.in_progress}
                      </span>
                      <span style={{ fontSize: '0.8rem', padding: '2px 6px', borderRadius: 4, background: '#f5f5f5', color: '#9ca3af' }}>
                        Pending: {tree.progress.pending}
                      </span>
                      {tree.progress.failed > 0 && (
                        <span style={{ fontSize: '0.8rem', padding: '2px 6px', borderRadius: 4, background: '#ffebee', color: '#ef4444' }}>
                          Failed: {tree.progress.failed}
                        </span>
                      )}
                    </div>
                    <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 8, height: 8 }}>
                      <div style={{
                        width: `${tree.progress.percentage}%`,
                        background: `linear-gradient(90deg, #ef4444, #f59e0b, #22c55e)`,
                        height: '100%',
                        borderRadius: 4,
                      }} />
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button className="btn-sm" style={{ background: '#4f6ef7', color: '#fff', border: 'none' }} onClick={() => handleViewTree(tree.goal_id)}>
                      View Details
                    </button>
                    <button className="btn-sm" style={{ background: '#8b5cf6', color: '#fff', border: 'none' }} onClick={() => handleNextLayer(tree.goal_id)}>
                      Next Layer
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Detail */}
      {activeSection === 'detail' && (
        <div className="dashboard-section">
          {treeLoading ? (
            <div className="panel-loading"><div className="spinner" /><span>Loading tree details...</span></div>
          ) : selectedTree ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <h3>{selectedTree.description}</h3>
                  <span className="dashboard-badge" style={{ background: strategyColors[selectedTree.strategy] || '#666', color: '#fff', display: 'inline-block', marginTop: 4 }}>
                    {selectedTree.strategy.replace(/_/g, ' ')}
                  </span>
                </div>
                <button className="btn-sm" style={{ background: '#4f6ef7', color: '#fff', border: 'none' }} onClick={() => handleNextLayer(selectedTree.goal_id)}>
                  Generate Next Layer
                </button>
              </div>

              {/* Progress */}
              <div style={{ marginBottom: 20, padding: 16, background: '#f8fafc', borderRadius: 8 }}>
                <h4>Progress Overview</h4>
                <div style={{ display: 'flex', gap: 16, marginTop: 8, flexWrap: 'wrap' }}>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value">{selectedTree.progress.total}</span>
                      <span className="stat-label">Total</span>
                    </div>
                  </div>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value" style={{ color: '#22c55e' }}>{selectedTree.progress.completed}</span>
                      <span className="stat-label">Completed</span>
                    </div>
                  </div>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value" style={{ color: '#3b82f6' }}>{selectedTree.progress.in_progress}</span>
                      <span className="stat-label">In Progress</span>
                    </div>
                  </div>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value" style={{ color: '#9ca3af' }}>{selectedTree.progress.pending}</span>
                      <span className="stat-label">Pending</span>
                    </div>
                  </div>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value" style={{ color: '#ef4444' }}>{selectedTree.progress.failed}</span>
                      <span className="stat-label">Failed</span>
                    </div>
                  </div>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value" style={{ color: '#4f6ef7' }}>{selectedTree.progress.percentage.toFixed(0)}%</span>
                      <span className="stat-label">Progress</span>
                    </div>
                  </div>
                </div>
                <div style={{ width: '100%', background: '#e5e7eb', borderRadius: 4, marginTop: 12, height: 10 }}>
                  <div style={{
                    width: `${selectedTree.progress.percentage}%`,
                    background: `linear-gradient(90deg, #ef4444, #f59e0b, #22c55e)`,
                    height: '100%',
                    borderRadius: 4,
                  }} />
                </div>
              </div>

              {/* Execution Order */}
              {selectedTree.execution_order.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <h4>Execution Order</h4>
                  <div className="forge-skill-list">
                    {selectedTree.execution_order.map((layer, layerIdx) => (
                      <div key={layerIdx} style={{
                        padding: 12,
                        marginBottom: 8,
                        background: '#f3f4f6',
                        borderRadius: 8,
                        borderLeft: `4px solid ${strategyColors[selectedTree.strategy] || '#4f6ef7'}`,
                      }}>
                        <div style={{ fontWeight: 700, marginBottom: 8, color: '#374151' }}>
                          Layer {layerIdx + 1} ({layer.length} sub-goal{layer.length !== 1 ? 's' : ''})
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {layer.map((sgId: string) => {
                            const sg = selectedTree.sub_goals.find(s => s.sub_goal_id === sgId);
                            const isCritical = selectedTree.critical_path.includes(sgId);
                            return (
                              <div key={sgId} style={{
                                padding: '6px 12px',
                                background: isCritical ? '#fef3c7' : '#fff',
                                borderRadius: 6,
                                border: `1px solid ${isCritical ? '#f59e0b' : '#d1d5db'}`,
                                fontSize: '0.85rem',
                                position: 'relative',
                              }}>
                                {sg?.description || sgId}
                                {isCritical && (
                                  <span style={{
                                    fontSize: '0.7rem',
                                    color: '#f59e0b',
                                    marginLeft: 6,
                                    fontWeight: 700,
                                  }}>
                                    ★ CRITICAL
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Critical Path */}
              {selectedTree.critical_path.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <h4>Critical Path</h4>
                  <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, padding: 12, background: '#fffbeb', borderRadius: 8, border: '1px solid #fde68a' }}>
                    {selectedTree.critical_path.map((sgId, idx) => {
                      const sg = selectedTree.sub_goals.find(s => s.sub_goal_id === sgId);
                      return (
                        <React.Fragment key={sgId}>
                          <span style={{
                            padding: '4px 10px',
                            background: '#fef3c7',
                            borderRadius: 6,
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: '#92400e',
                          }}>
                            {sg?.description || sgId}
                          </span>
                          {idx < selectedTree.critical_path.length - 1 && (
                            <span style={{ color: '#f59e0b', fontWeight: 700 }}>→</span>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Sub-Goals List */}
              <div style={{ marginBottom: 20 }}>
                <h4>All Sub-Goals ({selectedTree.sub_goals.length})</h4>
                <div className="forge-skill-list">
                  {selectedTree.sub_goals.map((sg: SubGoalInfo) => (
                    <div key={sg.sub_goal_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{sg.description}</div>
                        <span className="dashboard-badge" style={{
                          background: statusColors[sg.status] || '#9ca3af',
                          color: '#fff',
                        }}>
                          {statusLabels[sg.status] || sg.status}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>Type: {sg.sub_goal_type} | Priority: {sg.priority} | Effort: {sg.estimated_effort}</div>
                        <div>Agent: {sg.assigned_agent || 'Unassigned'}</div>
                        {sg.dependencies.length > 0 && (
                          <div>Dependencies: {sg.dependencies.join(', ')}</div>
                        )}
                        {sg.tags.length > 0 && (
                          <div style={{ marginTop: 4 }}>
                            {sg.tags.map(tag => (
                              <span key={tag} style={{
                                display: 'inline-block',
                                padding: '2px 8px',
                                margin: '2px',
                                background: '#e8eaf6',
                                color: '#4f6ef7',
                                borderRadius: 12,
                                fontSize: '0.75rem',
                              }}>{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Meta Info */}
              <div style={{ padding: 12, background: '#f9fafb', borderRadius: 8, fontSize: '0.85rem', color: '#6b7280' }}>
                <div>Goal ID: {selectedTree.goal_id}</div>
                <div>Created: {new Date(selectedTree.created_at).toLocaleString()}</div>
                <div>Updated: {new Date(selectedTree.updated_at).toLocaleString()}</div>
                <div>Tags: {selectedTree.tags.join(', ') || 'none'}</div>
              </div>
            </>
          ) : (
            <div className="panel-empty">Select a goal tree from the Trees tab to view details</div>
          )}
        </div>
      )}
    </div>
  );
};

export default GoalDecomposerPanel;