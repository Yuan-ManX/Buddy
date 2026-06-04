import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ExecutionPlan, PlanStep } from '../types';

export const PlanView: React.FC = () => {
  const [plans, setPlans] = useState<ExecutionPlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<ExecutionPlan | null>(null);
  const [agentId, setAgentId] = useState('');
  const [goal, setGoal] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [agents, setAgents] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    loadPlans();
    loadAgents();
  }, []);

  const loadPlans = async () => {
    try {
      const data = await api.plans.list();
      setPlans(data);
    } catch (e) {
      setError('Failed to load plans');
    }
  };

  const loadAgents = async () => {
    try {
      const data = await api.agents.list();
      setAgents(data.items.map(a => ({ id: a.id, name: a.name })));
      if (data.items.length > 0) setAgentId(data.items[0].id);
    } catch {}
  };

  const generatePlan = async () => {
    if (!agentId || !goal.trim()) return;
    setLoading(true);
    setError('');
    try {
      const plan = await api.plans.generate(agentId, goal);
      setPlans(prev => [plan, ...prev]);
      setSelectedPlan(plan);
      setGoal('');
    } catch (e: any) {
      setError(e.message || 'Failed to generate plan');
    } finally {
      setLoading(false);
    }
  };

  const executePlan = async (planId: string) => {
    if (!agentId) return;
    setLoading(true);
    setError('');
    try {
      const updated = await api.plans.execute(planId, agentId);
      setPlans(prev => prev.map(p => p.id === updated.id ? updated : p));
      setSelectedPlan(updated);
    } catch (e: any) {
      setError(e.message || 'Failed to execute plan');
    } finally {
      setLoading(false);
    }
  };

  const cancelPlan = async (planId: string) => {
    try {
      await api.plans.cancel(planId);
      loadPlans();
    } catch (e: any) {
      setError(e.message || 'Failed to cancel plan');
    }
  };

  const deletePlan = async (planId: string) => {
    try {
      await api.plans.delete(planId);
      setPlans(prev => prev.filter(p => p.id !== planId));
      if (selectedPlan?.id === planId) setSelectedPlan(null);
    } catch (e: any) {
      setError(e.message || 'Failed to delete plan');
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: '#9ca3af',
      approved: '#3b82f6',
      in_progress: '#f59e0b',
      completed: '#10b981',
      failed: '#ef4444',
      cancelled: '#6b7280',
    };
    return colors[status] || '#6b7280';
  };

  const getStepStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: '#d1d5db',
      blocked: '#f87171',
      in_progress: '#fbbf24',
      completed: '#34d399',
      skipped: '#9ca3af',
      failed: '#ef4444',
    };
    return colors[status] || '#d1d5db';
  };

  return (
    <div className="plan-view">
      <h2>Plan Mode</h2>
      <p className="subtitle">Decompose complex goals into executable plans</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="plan-generate">
        <select value={agentId} onChange={e => setAgentId(e.target.value)}>
          <option value="">Select agent...</option>
          {agents.map(a => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Describe your goal..."
          value={goal}
          onChange={e => setGoal(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && generatePlan()}
        />
        <button onClick={generatePlan} disabled={loading || !agentId || !goal.trim()}>
          {loading ? 'Generating...' : 'Generate Plan'}
        </button>
      </div>

      <div className="plan-layout">
        <div className="plan-list">
          <h3>Plans ({plans.length})</h3>
          {plans.map(plan => (
            <div
              key={plan.id}
              className={`plan-card ${selectedPlan?.id === plan.id ? 'selected' : ''}`}
              onClick={() => setSelectedPlan(plan)}
            >
              <div className="plan-card-header">
                <span className="plan-title">{plan.title}</span>
                <span className="plan-status" style={{ background: getStatusColor(plan.status) }}>
                  {plan.status}
                </span>
              </div>
              <div className="plan-progress-bar">
                <div
                  className="plan-progress-fill"
                  style={{ width: `${plan.progress?.percentage || 0}%` }}
                />
              </div>
              <div className="plan-meta">
                <span>{plan.progress?.percentage || 0}% complete</span>
                <span>{plan.steps?.length || 0} steps</span>
              </div>
            </div>
          ))}
          {plans.length === 0 && (
            <div className="empty-state">No plans yet. Generate one above.</div>
          )}
        </div>

        <div className="plan-detail">
          {selectedPlan ? (
            <>
              <div className="plan-detail-header">
                <div>
                  <h3>{selectedPlan.title}</h3>
                  <p className="plan-goal">{selectedPlan.goal}</p>
                </div>
                <div className="plan-actions">
                  {selectedPlan.status === 'approved' && (
                    <button
                      className="btn-execute"
                      onClick={() => executePlan(selectedPlan.id)}
                      disabled={loading}
                    >
                      Execute Plan
                    </button>
                  )}
                  {['draft', 'approved', 'in_progress'].includes(selectedPlan.status) && (
                    <button className="btn-cancel" onClick={() => cancelPlan(selectedPlan.id)}>
                      Cancel
                    </button>
                  )}
                  <button className="btn-delete" onClick={() => deletePlan(selectedPlan.id)}>
                    Delete
                  </button>
                </div>
              </div>

              <div className="plan-progress-large">
                <div className="progress-info">
                  <span>Progress: {selectedPlan.progress?.percentage || 0}%</span>
                  <span>
                    {selectedPlan.progress?.completed || 0}/{selectedPlan.progress?.total || 0} steps
                  </span>
                </div>
                <div className="plan-progress-bar large">
                  <div
                    className="plan-progress-fill"
                    style={{ width: `${selectedPlan.progress?.percentage || 0}%` }}
                  />
                </div>
              </div>

              <div className="plan-steps">
                <h4>Steps</h4>
                {selectedPlan.steps.map((step, i) => (
                  <div key={step.id} className="step-item">
                    <div className="step-indicator" style={{ background: getStepStatusColor(step.status) }}>
                      {step.status === 'completed' ? '✓' : step.status === 'failed' ? '✗' : step.status === 'in_progress' ? '●' : i + 1}
                    </div>
                    <div className="step-content">
                      <div className="step-title">{step.title}</div>
                      {step.description && <div className="step-desc">{step.description}</div>}
                      {step.depends_on.length > 0 && (
                        <div className="step-deps">
                          Depends on: {step.depends_on.join(', ')}
                        </div>
                      )}
                      {step.result && (
                        <div className="step-result">
                          <pre>{step.result}</pre>
                        </div>
                      )}
                    </div>
                    <div className="step-status" style={{ color: getStepStatusColor(step.status) }}>
                      {step.status}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="no-selection">Select a plan to view details</div>
          )}
        </div>
      </div>

      <style>{`
        .plan-view { padding: 24px; max-width: 1400px; margin: 0 auto; }
        .plan-view h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
        .subtitle { color: #6b7280; margin-bottom: 24px; }
        .plan-generate { display: flex; gap: 12px; margin-bottom: 24px; align-items: center; }
        .plan-generate select { padding: 10px 16px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.9rem; background: #fff; }
        .plan-generate input { flex: 1; padding: 10px 16px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.9rem; }
        .plan-generate button { padding: 10px 24px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; white-space: nowrap; }
        .plan-generate button:hover { background: #2563eb; }
        .plan-generate button:disabled { background: #9ca3af; cursor: not-allowed; }
        .plan-layout { display: grid; grid-template-columns: 340px 1fr; gap: 24px; }
        .plan-list { background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; max-height: 700px; overflow-y: auto; }
        .plan-list h3 { font-size: 0.9rem; color: #6b7280; margin-bottom: 12px; }
        .plan-card { padding: 12px; border-radius: 8px; cursor: pointer; margin-bottom: 8px; border: 1px solid #e5e7eb; transition: all 0.15s; }
        .plan-card:hover { border-color: #3b82f6; }
        .plan-card.selected { background: #eff6ff; border-color: #3b82f6; }
        .plan-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .plan-title { font-weight: 600; font-size: 0.9rem; }
        .plan-status { font-size: 0.7rem; color: #fff; padding: 2px 8px; border-radius: 10px; text-transform: uppercase; }
        .plan-progress-bar { height: 4px; background: #e5e7eb; border-radius: 2px; margin-bottom: 8px; overflow: hidden; }
        .plan-progress-bar.large { height: 8px; border-radius: 4px; margin: 8px 0; }
        .plan-progress-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 2px; transition: width 0.3s; }
        .plan-meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: #9ca3af; }
        .plan-detail { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; }
        .plan-detail-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
        .plan-detail h3 { font-size: 1.2rem; font-weight: 700; margin-bottom: 4px; }
        .plan-goal { color: #6b7280; font-size: 0.9rem; }
        .plan-actions { display: flex; gap: 8px; }
        .btn-execute { padding: 8px 16px; background: #10b981; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
        .btn-execute:hover { background: #059669; }
        .btn-execute:disabled { background: #9ca3af; cursor: not-allowed; }
        .btn-cancel { padding: 8px 16px; background: #f59e0b; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
        .btn-cancel:hover { background: #d97706; }
        .btn-delete { padding: 8px 16px; background: #ef4444; color: #fff; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
        .btn-delete:hover { background: #dc2626; }
        .plan-progress-large { margin-bottom: 24px; }
        .progress-info { display: flex; justify-content: space-between; font-size: 0.85rem; color: #6b7280; margin-bottom: 4px; }
        .plan-steps { margin-top: 16px; }
        .plan-steps h4 { font-size: 0.9rem; color: #374151; margin-bottom: 12px; }
        .step-item { display: flex; gap: 12px; padding: 12px; border: 1px solid #f3f4f6; border-radius: 8px; margin-bottom: 8px; align-items: flex-start; }
        .step-item:hover { background: #f9fafb; }
        .step-indicator { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }
        .step-content { flex: 1; }
        .step-title { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
        .step-desc { font-size: 0.8rem; color: #6b7280; margin-bottom: 4px; }
        .step-deps { font-size: 0.75rem; color: #9ca3af; font-style: italic; }
        .step-result { margin-top: 8px; }
        .step-result pre { font-size: 0.8rem; background: #f9fafb; padding: 8px; border-radius: 4px; max-height: 100px; overflow-y: auto; white-space: pre-wrap; }
        .step-status { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; flex-shrink: 0; }
        .no-selection { color: #9ca3af; text-align: center; padding: 60px; }
        .empty-state { color: #9ca3af; text-align: center; padding: 40px; font-size: 0.9rem; }
        .error-banner { background: #fef2f2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.9rem; }
      `}</style>
    </div>
  );
};