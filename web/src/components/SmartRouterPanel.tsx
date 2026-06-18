import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { SmartRouterStats, RoutingDecision, ComplexityAnalysis, RouterModelConfig } from '../types';

export const SmartRouterPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<SmartRouterStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'routing' | 'models' | 'analyze'>('overview');
  const [testPrompt, setTestPrompt] = useState('');
  const [testResult, setTestResult] = useState<RoutingDecision | null>(null);
  const [analyzePrompt, setAnalyzePrompt] = useState('');
  const [analyzeResult, setAnalyzeResult] = useState<ComplexityAnalysis | null>(null);
  const [showRegisterModel, setShowRegisterModel] = useState(false);
  const [modelForm, setModelForm] = useState({
    provider: 'openai', model_name: '', tier: 'standard',
    cost_per_1k_tokens: '0.001', max_tokens: '4096', latency_ms: '500',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.smartRouter.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load router data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleTestRoute = async () => {
    if (!testPrompt.trim()) return;
    try {
      const result = await api.smartRouter.select({ prompt: testPrompt });
      setTestResult(result);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAnalyze = async () => {
    if (!analyzePrompt.trim()) return;
    try {
      const result = await api.smartRouter.analyze(analyzePrompt);
      setAnalyzeResult(result);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRegisterModel = async () => {
    if (!modelForm.model_name.trim()) return;
    try {
      await api.smartRouter.registerModel({
        provider: modelForm.provider,
        model_name: modelForm.model_name,
        tier: modelForm.tier,
        cost_per_1k_tokens: parseFloat(modelForm.cost_per_1k_tokens),
        max_tokens: parseInt(modelForm.max_tokens),
        latency_ms: parseInt(modelForm.latency_ms),
      });
      toast.success('Model registered');
      setShowRegisterModel(false);
      setModelForm({ provider: 'openai', model_name: '', tier: 'standard', cost_per_1k_tokens: '0.001', max_tokens: '4096', latency_ms: '500' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const tierColors: Record<string, string> = {
    light: '#22c55e', standard: '#3b82f6', premium: '#8b5cf6',
  };

  const complexityColors: Record<string, string> = {
    trivial: '#9ca3af', simple: '#22c55e', moderate: '#f59e0b', complex: '#f97316', expert: '#ef4444',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Smart Router</h2>
          <p className="panel-subtitle">Intelligent model routing with cost optimization</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading router data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Smart Router</h2>
        <p className="panel-subtitle">Task complexity analysis → Optimal model tier → Cost savings</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_models}</span><span className="stat-label">Models</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_decisions}</span><span className="stat-label">Decisions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">${stats.cost_savings.total_savings.toFixed(4)}</span><span className="stat-label">Saved</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.cost_savings.total_routing_decisions}</span><span className="stat-label">Routings</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'routing', 'models', 'analyze'] as const).map(s => (
          <button key={s} className={`forge-tab ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Model Distribution</h3>
          {Object.entries(stats.models_by_tier).map(([tier, models]) => (
            <div key={tier} style={{marginBottom: 16}}>
              <h4 style={{color: tierColors[tier] || '#666', textTransform: 'capitalize'}}>{tier} Tier</h4>
              <div className="forge-skill-list">
                {models.map((m: RouterModelConfig) => (
                  <div key={m.model_name} className="forge-skill-card">
                    <div className="forge-skill-header">
                      <div className="forge-skill-name">{m.provider}/{m.model_name}</div>
                      <span className="dashboard-badge" style={{background: tierColors[m.tier] || '#666', color: '#fff'}}>{m.tier}</span>
                    </div>
                    <div className="forge-skill-meta">
                      <div>Cost: ${m.cost_per_1k_tokens}/1k tokens | Max: {m.max_tokens.toLocaleString()} tokens</div>
                      <div>Latency: {m.latency_ms}ms | Reliability: {(m.reliability_score * 100).toFixed(0)}%</div>
                      <div>
                        {m.supports_tools && <span className="dashboard-badge active" style={{marginRight: 4}}>Tools</span>}
                        {m.supports_vision && <span className="dashboard-badge active">Vision</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <h3 style={{marginTop: 20}}>Complexity Distribution</h3>
          {Object.entries(stats.distribution).map(([complexity, count]) => (
            <div key={complexity} className="dashboard-stat-row">
              <span style={{color: complexityColors[complexity] || '#666', textTransform: 'capitalize'}}>{complexity}</span>
              <strong>{count}</strong>
            </div>
          ))}

          <h3 style={{marginTop: 20}}>Cost Savings Per Model</h3>
          {Object.entries(stats.cost_savings.per_model).map(([model, savings]) => (
            <div key={model} className="dashboard-stat-row">
              <span>{model}</span>
              <strong style={{color: '#22c55e'}}>${savings.toFixed(4)}</strong>
            </div>
          ))}
        </div>
      )}

      {/* Routing Test */}
      {activeSection === 'routing' && (
        <div className="dashboard-section">
          <h3>Test Route Selection</h3>
          <div className="form-group">
            <label>Enter a prompt to test routing</label>
            <textarea
              rows={4}
              value={testPrompt}
              onChange={e => setTestPrompt(e.target.value)}
              placeholder="e.g., Build a full-stack web application with authentication and a database"
            />
          </div>
          <button className="btn-primary" onClick={handleTestRoute}>Route This Prompt</button>

          {testResult && (
            <div className="forge-skill-card" style={{marginTop: 16}}>
              <div className="forge-skill-header">
                <div className="forge-skill-name">Routing Decision</div>
                <span className="dashboard-badge" style={{background: complexityColors[testResult.task_complexity] || '#666', color: '#fff'}}>{testResult.task_complexity}</span>
              </div>
              <div className="forge-skill-meta">
                <div><strong>Selected:</strong> {testResult.selected_model.provider}/{testResult.selected_model.model_name} ({testResult.selected_model.tier})</div>
                <div><strong>Estimated Cost:</strong> ${testResult.estimated_cost.toFixed(6)} | <strong>Tokens:</strong> {testResult.estimated_tokens}</div>
                <div><strong>Confidence:</strong> {(testResult.confidence * 100).toFixed(1)}%</div>
                <div style={{color: '#6b7280', fontSize: '0.85rem', marginTop: 4}}>{testResult.reasoning}</div>
              </div>
              {testResult.alternative_model && (
                <div style={{marginTop: 8, padding: 8, background: '#f3f4f6', borderRadius: 6, fontSize: '0.85rem'}}>
                  <strong>Alternative:</strong> {testResult.alternative_model.provider}/{testResult.alternative_model.model_name} ({testResult.alternative_model.tier})
                </div>
              )}
            </div>
          )}

          {stats && stats.recent_decisions.length > 0 && (
            <div style={{marginTop: 20}}>
              <h3>Recent Decisions</h3>
              {stats.recent_decisions.slice(0, 10).map((d: RoutingDecision, i: number) => (
                <div key={i} className="forge-skill-card" style={{marginBottom: 8}}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{d.selected_model.model_name}</div>
                    <span className="dashboard-badge" style={{background: complexityColors[d.task_complexity] || '#666', color: '#fff'}}>{d.task_complexity}</span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Cost: ${d.estimated_cost.toFixed(6)} | {new Date(d.timestamp).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Models Management */}
      {activeSection === 'models' && (
        <div className="dashboard-section">
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16}}>
            <h3>Registered Models</h3>
            <button className="btn-primary-sm" onClick={() => setShowRegisterModel(!showRegisterModel)}>
              {showRegisterModel ? 'Cancel' : '+ Register Model'}
            </button>
          </div>

          {showRegisterModel && (
            <div className="skill-execute" style={{marginBottom: 16, position: 'static'}}>
              <h3>Register New Model</h3>
              <div className="form-row">
                <div className="form-group">
                  <label>Provider</label>
                  <select value={modelForm.provider} onChange={e => setModelForm(f => ({...f, provider: e.target.value}))}>
                    {['openai', 'anthropic', 'google', 'meta', 'mistral', 'custom'].map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{flex: 2}}>
                  <label>Model Name</label>
                  <input type="text" value={modelForm.model_name} onChange={e => setModelForm(f => ({...f, model_name: e.target.value}))} placeholder="gpt-4o" />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Tier</label>
                  <select value={modelForm.tier} onChange={e => setModelForm(f => ({...f, tier: e.target.value}))}>
                    {['light', 'standard', 'premium'].map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Cost per 1K tokens ($)</label>
                  <input type="text" value={modelForm.cost_per_1k_tokens} onChange={e => setModelForm(f => ({...f, cost_per_1k_tokens: e.target.value}))} />
                </div>
                <div className="form-group">
                  <label>Max Tokens</label>
                  <input type="text" value={modelForm.max_tokens} onChange={e => setModelForm(f => ({...f, max_tokens: e.target.value}))} />
                </div>
                <div className="form-group">
                  <label>Latency (ms)</label>
                  <input type="text" value={modelForm.latency_ms} onChange={e => setModelForm(f => ({...f, latency_ms: e.target.value}))} />
                </div>
              </div>
              <button className="btn-primary" onClick={handleRegisterModel}>Register Model</button>
            </div>
          )}

          {stats && Object.entries(stats.models_by_tier).map(([tier, models]) => (
            <div key={tier} style={{marginBottom: 16}}>
              <h4 style={{color: tierColors[tier] || '#666', textTransform: 'capitalize'}}>{tier} ({models.length})</h4>
              {models.map((m: RouterModelConfig) => (
                <div key={m.model_name} className="forge-skill-card" style={{marginBottom: 8}}>
                  <div className="forge-skill-header"><div className="forge-skill-name">{m.provider}/{m.model_name}</div></div>
                  <div className="forge-skill-meta">
                    <div>${m.cost_per_1k_tokens}/1K tokens | {m.max_tokens.toLocaleString()} max | {m.latency_ms}ms</div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Analyze Complexity */}
      {activeSection === 'analyze' && (
        <div className="dashboard-section">
          <h3>Analyze Task Complexity</h3>
          <div className="form-group">
            <label>Enter a prompt to analyze its complexity</label>
            <textarea
              rows={4}
              value={analyzePrompt}
              onChange={e => setAnalyzePrompt(e.target.value)}
              placeholder="e.g., What is the capital of France?"
            />
          </div>
          <button className="btn-primary" onClick={handleAnalyze}>Analyze</button>

          {analyzeResult && (
            <div className="forge-skill-card" style={{marginTop: 16}}>
              <div className="forge-skill-header">
                <div className="forge-skill-name">Complexity Analysis</div>
                <span className="dashboard-badge" style={{background: complexityColors[analyzeResult.complexity] || '#666', color: '#fff', textTransform: 'capitalize'}}>{analyzeResult.complexity}</span>
              </div>
              <div className="forge-skill-meta">
                <div><strong>Score:</strong> {(analyzeResult.score * 100).toFixed(1)}%</div>
                <div><strong>Recommended Tier:</strong> <span style={{color: tierColors[analyzeResult.recommended_tier] || '#666', fontWeight: 700, textTransform: 'capitalize'}}>{analyzeResult.recommended_tier}</span></div>
              </div>
              <div style={{marginTop: 8}}>
                <div style={{width: '100%', background: '#e5e7eb', borderRadius: 4, height: 10}}>
                  <div style={{
                    width: `${analyzeResult.score * 100}%`,
                    background: `linear-gradient(90deg, #22c55e, #f59e0b, #ef4444)`,
                    height: '100%',
                    borderRadius: 4,
                  }} />
                </div>
                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#9ca3af', marginTop: 4}}>
                  <span>Trivial</span><span>Simple</span><span>Moderate</span><span>Complex</span><span>Expert</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SmartRouterPanel;