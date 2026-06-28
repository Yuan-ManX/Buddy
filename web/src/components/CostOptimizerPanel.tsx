import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#d97706',
  secondary: '#fcd34d',
  bg: '#fffbeb',
  border: '#fde68a',
  accent: '#fef3c7',
  text: '#78350f',
};

const MODEL_TIERS = ['lite', 'standard', 'premium', 'flagship'];
const ROUTE_STRATEGIES = ['cost_first', 'quality_first', 'balanced', 'latency_first'];

export const CostOptimizerPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'model' | 'assess' | 'route'>('overview');

  // Model form
  const [modelForm, setModelForm] = useState({
    name: '', provider: '', tier: 'standard',
    cost_per_1k_input: '', cost_per_1k_output: '', quality_score: '', max_context: '',
  });

  // Assess form
  const [assessForm, setAssessForm] = useState({
    description: '', estimated_tokens: '',
  });
  const [assessResult, setAssessResult] = useState<any>(null);

  // Route form
  const [routeForm, setRouteForm] = useState({
    task_id: '', strategy: 'balanced',
  });
  const [routeResult, setRouteResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.costOptimizer.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load cost optimizer data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRegisterModel = async () => {
    if (!modelForm.name.trim() || !modelForm.provider.trim()) return;
    try {
      await api.costOptimizer.registerModel({
        name: modelForm.name.trim(),
        provider: modelForm.provider.trim(),
        tier: modelForm.tier,
        cost_per_1k_input: Number(modelForm.cost_per_1k_input) || 0,
        cost_per_1k_output: Number(modelForm.cost_per_1k_output) || 0,
        quality_score: modelForm.quality_score ? Number(modelForm.quality_score) : undefined,
        max_context: modelForm.max_context ? Number(modelForm.max_context) : undefined,
      });
      toast.success(`Model "${modelForm.name}" registered`);
      setModelForm({
        name: '', provider: '', tier: 'standard',
        cost_per_1k_input: '', cost_per_1k_output: '', quality_score: '', max_context: '',
      });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAssess = async () => {
    if (!assessForm.description.trim()) return;
    try {
      const result = await api.costOptimizer.assessComplexity({
        description: assessForm.description.trim(),
        estimated_tokens: assessForm.estimated_tokens ? Number(assessForm.estimated_tokens) : undefined,
      });
      setAssessResult(result);
      toast.success('Complexity assessed');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRoute = async () => {
    if (!routeForm.task_id.trim()) return;
    try {
      const result = await api.costOptimizer.route({
        task_id: routeForm.task_id.trim(),
        strategy: routeForm.strategy,
      });
      setRouteResult(result);
      toast.success('Task routed');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>💰 Cost Optimizer</h2>
          <p className="panel-subtitle">Register models, assess complexity, and optimize routing</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading cost optimizer...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>💰 Cost Optimizer</h2>
        <p className="panel-subtitle">Register models, assess complexity, and optimize routing</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_models ?? '-'}</span><span className="stat-label">Models</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_assessments ?? '-'}</span><span className="stat-label">Assessments</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_routes ?? '-'}</span><span className="stat-label">Routes</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.estimated_savings ?? '-'}</span><span className="stat-label">Est. Savings</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'model', 'assess', 'route'] as const).map(s => (
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

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Cost Optimizer Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Models</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_models ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Assessments</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_assessments ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Routes</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_routes ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Est. Savings</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.estimated_savings ?? 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Model */}
      {activeSection === 'model' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Register Model</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={modelForm.name}
                  onChange={e => setModelForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. gpt-4o"
                />
              </div>
              <div className="form-group">
                <label>Provider *</label>
                <input
                  type="text"
                  value={modelForm.provider}
                  onChange={e => setModelForm(f => ({ ...f, provider: e.target.value }))}
                  placeholder="e.g. openai"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Tier</label>
                <select value={modelForm.tier} onChange={e => setModelForm(f => ({ ...f, tier: e.target.value }))}>
                  {MODEL_TIERS.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Quality Score (0-1)</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={modelForm.quality_score}
                  onChange={e => setModelForm(f => ({ ...f, quality_score: e.target.value }))}
                  placeholder="0.0 - 1.0"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Cost / 1K Input ($)</label>
                <input
                  type="number"
                  min="0"
                  step="0.0001"
                  value={modelForm.cost_per_1k_input}
                  onChange={e => setModelForm(f => ({ ...f, cost_per_1k_input: e.target.value }))}
                  placeholder="0.005"
                />
              </div>
              <div className="form-group">
                <label>Cost / 1K Output ($)</label>
                <input
                  type="number"
                  min="0"
                  step="0.0001"
                  value={modelForm.cost_per_1k_output}
                  onChange={e => setModelForm(f => ({ ...f, cost_per_1k_output: e.target.value }))}
                  placeholder="0.015"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Max Context (tokens)</label>
              <input
                type="number"
                min="0"
                value={modelForm.max_context}
                onChange={e => setModelForm(f => ({ ...f, max_context: e.target.value }))}
                placeholder="e.g. 128000"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRegisterModel}
              disabled={!modelForm.name.trim() || !modelForm.provider.trim()}
            >
              Register Model
            </button>
          </div>
        </div>
      )}

      {/* Assess */}
      {activeSection === 'assess' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Assess Complexity</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Description *</label>
              <textarea
                rows={4}
                value={assessForm.description}
                onChange={e => setAssessForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the task to assess..."
              />
            </div>
            <div className="form-group">
              <label>Estimated Tokens</label>
              <input
                type="number"
                min="0"
                value={assessForm.estimated_tokens}
                onChange={e => setAssessForm(f => ({ ...f, estimated_tokens: e.target.value }))}
                placeholder="Optional token estimate"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAssess}
              disabled={!assessForm.description.trim()}
            >
              Assess
            </button>
          </div>

          {assessResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Assessment Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(assessResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Route */}
      {activeSection === 'route' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Route Task</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Task ID *</label>
                <input
                  type="text"
                  value={routeForm.task_id}
                  onChange={e => setRouteForm(f => ({ ...f, task_id: e.target.value }))}
                  placeholder="Task ID"
                />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={routeForm.strategy} onChange={e => setRouteForm(f => ({ ...f, strategy: e.target.value }))}>
                  {ROUTE_STRATEGIES.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleRoute}
              disabled={!routeForm.task_id.trim()}
            >
              Route Task
            </button>
          </div>

          {routeResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Route Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(routeResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CostOptimizerPanel;
