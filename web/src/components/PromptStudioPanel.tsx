import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#6d28d9',
  secondary: '#a78bfa',
  bg: '#faf5ff',
  border: '#c4b5fd',
  accent: '#ede9fe',
  text: '#4c1d95',
};

export const PromptStudioPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'prompts' | 'abtest' | 'optimize' | 'chain'>('overview');

  const [createForm, setCreateForm] = useState({
    name: '', content: '', type: 'system', category: '', tags: '', description: '',
  });
  const [prompts, setPrompts] = useState<any[]>([]);
  const [selectedPromptVersions, setSelectedPromptVersions] = useState<any[] | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(false);

  const [abTestForm, setABTestForm] = useState({
    name: '', prompt_a_id: '', prompt_b_id: '', metric: 'quality',
  });
  const [optimizeForm, setOptimizeForm] = useState({ prompt_id: '', strategy: 'clarity' });
  const [optimizeResult, setOptimizeResult] = useState<any>(null);

  const [chainForm, setChainForm] = useState({
    name: '', steps: '', description: '',
  });
  const [executeChainForm, setExecuteChainForm] = useState({
    chain_id: '', variables: '',
  });
  const [chains, setChains] = useState<any[]>([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, pList] = await Promise.all([
        api.promptStudio.stats(),
        api.promptStudio.list(),
      ]);
      setStats(s);
      setPrompts(pList.prompts || pList.items || pList);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load prompt studio data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!createForm.name.trim() || !createForm.content.trim()) return;
    try {
      await api.promptStudio.create({
        name: createForm.name,
        content: createForm.content,
        type: createForm.type || undefined,
        category: createForm.category || undefined,
        tags: createForm.tags ? createForm.tags.split(',').map(s => s.trim()) : undefined,
        description: createForm.description || undefined,
      });
      toast.success('Prompt created');
      setCreateForm({ name: '', content: '', type: 'system', category: '', tags: '', description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleViewVersions = async (promptId: string) => {
    try {
      setVersionsLoading(true);
      const versions = await api.promptStudio.versions(promptId);
      setSelectedPromptVersions(versions.versions || versions.items || versions);
      toast.success('Versions loaded');
    } catch (e: any) { toast.error(e.message); }
    finally { setVersionsLoading(false); }
  };

  const handleCreateABTest = async () => {
    if (!abTestForm.name.trim() || !abTestForm.prompt_a_id.trim() || !abTestForm.prompt_b_id.trim()) return;
    try {
      await api.promptStudio.createABTest({
        name: abTestForm.name,
        prompt_a_id: abTestForm.prompt_a_id,
        prompt_b_id: abTestForm.prompt_b_id,
        metric: abTestForm.metric || undefined,
      });
      toast.success('A/B test created');
      setABTestForm({ name: '', prompt_a_id: '', prompt_b_id: '', metric: 'quality' });
    } catch (e: any) { toast.error(e.message); }
  };

  const handleOptimize = async () => {
    if (!optimizeForm.prompt_id.trim()) return;
    try {
      const result = await api.promptStudio.optimize({
        prompt_id: optimizeForm.prompt_id,
        strategy: optimizeForm.strategy || undefined,
      });
      setOptimizeResult(result);
      toast.success('Optimization completed');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleCreateChain = async () => {
    if (!chainForm.name.trim() || !chainForm.steps.trim()) return;
    try {
      await api.promptStudio.createChain({
        name: chainForm.name,
        steps: chainForm.steps.split(',').map(s => s.trim()),
        description: chainForm.description || undefined,
      });
      toast.success('Chain created');
      setChainForm({ name: '', steps: '', description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleExecuteChain = async () => {
    if (!executeChainForm.chain_id.trim()) return;
    try {
      let vars: Record<string, string> | undefined;
      if (executeChainForm.variables.trim()) {
        vars = {};
        executeChainForm.variables.split(',').forEach(pair => {
          const [k, v] = pair.split('=').map(s => s.trim());
          if (k && v) vars![k] = v;
        });
      }
      await api.promptStudio.executeChain({
        chain_id: executeChainForm.chain_id,
        variables: vars,
      });
      toast.success('Chain executed');
      setExecuteChainForm({ chain_id: '', variables: '' });
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>✍️ Prompt Studio</h2>
          <p className="panel-subtitle">Create, test, optimize, and chain prompts for maximum effectiveness</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading prompt studio...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>✍️ Prompt Studio</h2>
        <p className="panel-subtitle">Create, test, optimize, and chain prompts for maximum effectiveness</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_prompts ?? stats.prompt_count ?? '-'}</span><span className="stat-label">Total Prompts</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_versions ?? stats.version_count ?? '-'}</span><span className="stat-label">Versions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_tests ?? stats.ab_test_count ?? '-'}</span><span className="stat-label">A/B Tests</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{color: themeColors.primary}}>{stats.total_chains ?? stats.chain_count ?? '-'}</span><span className="stat-label">Chains</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'prompts', 'abtest', 'optimize', 'chain'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s === 'abtest' ? 'A/B Test' : s === 'prompts' ? 'Prompt List' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {Object.entries(stats).filter(([k]) => !['by_type', 'by_category', 'recent_prompts'].includes(k)).map(([key, value]: [string, any]) => (
              <div key={key} style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontSize: '0.85rem', color: '#6b7280', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>
                  {typeof value === 'number' ? value : typeof value === 'object' ? JSON.stringify(value).slice(0, 40) : String(value)}
                </div>
              </div>
            ))}
          </div>
          {stats.by_type && Object.keys(stats.by_type).length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h4 style={{ color: themeColors.text }}>By Type</h4>
              {Object.entries(stats.by_type).map(([type, count]: [string, any]) => (
                <div key={type} className="dashboard-stat-row">
                  <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{type}</span>
                  <strong style={{ color: themeColors.primary }}>{count}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Prompt */}
      {activeSection === 'create' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create New Prompt</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={createForm.name}
                onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                placeholder="summarize-document" />
            </div>
            <div className="form-group">
              <label>Description</label>
              <input type="text" value={createForm.description}
                onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Brief description of what this prompt does" />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={6}
                value={createForm.content}
                onChange={e => setCreateForm(f => ({ ...f, content: e.target.value }))}
                placeholder="You are an expert {{role}}. Your task is to {{task}}..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Type</label>
                <select value={createForm.type} onChange={e => setCreateForm(f => ({ ...f, type: e.target.value }))}>
                  {['system', 'user', 'assistant', 'function', 'template'].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Category</label>
                <input type="text" value={createForm.category}
                  onChange={e => setCreateForm(f => ({ ...f, category: e.target.value }))}
                  placeholder="summarization, analysis" />
              </div>
              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input type="text" value={createForm.tags}
                  onChange={e => setCreateForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="nlp, text, production" />
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleCreate}>Create Prompt</button>
          </div>
        </div>
      )}

      {/* Prompt List */}
      {activeSection === 'prompts' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>All Prompts ({prompts.length})</h3>
          {prompts.length === 0 ? (
            <div className="panel-empty">No prompts created yet. Go to the Create tab to make one.</div>
          ) : (
            <div className="forge-skill-list">
              {prompts.map((prompt: any, idx: number) => (
                <div key={prompt.id || prompt.prompt_id || idx} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.primary}` }}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ color: themeColors.text }}>{prompt.name || prompt.title}</div>
                    <span className="dashboard-badge" style={{ background: themeColors.primary, color: '#fff' }}>
                      {prompt.type || 'system'}
                    </span>
                  </div>
                  <div className="forge-skill-meta">
                    {prompt.description && <div>{prompt.description}</div>}
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 4, fontSize: '0.8rem', color: '#6b7280' }}>
                      {prompt.category && <span>Category: {prompt.category}</span>}
                      {prompt.version != null && <span>Version: {prompt.version}</span>}
                      {prompt.created_at && <span>Created: {new Date(prompt.created_at).toLocaleString()}</span>}
                    </div>
                    {prompt.tags?.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        {prompt.tags.map((tag: string) => (
                          <span key={tag} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px', background: themeColors.accent, color: themeColors.text, borderRadius: 12, fontSize: '0.75rem' }}>{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <button className="btn-sm" style={{ background: themeColors.primary, color: '#fff', border: 'none' }}
                      onClick={() => handleViewVersions(prompt.id || prompt.prompt_id)}>
                      View Versions
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Version History */}
          {selectedPromptVersions && (
            <div style={{ marginTop: 24, padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Version History</h4>
              {versionsLoading ? (
                <div className="panel-loading"><div className="spinner" /><span>Loading versions...</span></div>
              ) : Array.isArray(selectedPromptVersions) && selectedPromptVersions.length === 0 ? (
                <div className="panel-empty">No version history available</div>
              ) : (
                <div className="forge-skill-list" style={{ marginTop: 8 }}>
                  {Array.isArray(selectedPromptVersions) && selectedPromptVersions.map((v: any, vi: number) => (
                    <div key={v.version || vi} className="forge-skill-card" style={{ borderLeft: `4px solid ${themeColors.secondary}` }}>
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ color: themeColors.text }}>Version {v.version ?? vi + 1}</div>
                        <span className="dashboard-badge" style={{ background: themeColors.secondary, color: '#fff' }}>
                          {v.created_at ? new Date(v.created_at).toLocaleDateString() : ''}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem', color: themeColors.text }}>
                          {v.content || v.prompt_template || JSON.stringify(v, null, 2).slice(0, 300)}
                        </pre>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* A/B Test */}
      {activeSection === 'abtest' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create A/B Test</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Test Name</label>
              <input type="text" value={abTestForm.name}
                onChange={e => setABTestForm(f => ({ ...f, name: e.target.value }))}
                placeholder="summarization-v1-vs-v2" />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Prompt A ID</label>
                <select value={abTestForm.prompt_a_id} onChange={e => setABTestForm(f => ({ ...f, prompt_a_id: e.target.value }))}>
                  <option value="">Select prompt...</option>
                  {prompts.map((p: any, idx: number) => (
                    <option key={p.id || p.prompt_id || idx} value={p.id || p.prompt_id || idx}>{p.name || p.title}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Prompt B ID</label>
                <select value={abTestForm.prompt_b_id} onChange={e => setABTestForm(f => ({ ...f, prompt_b_id: e.target.value }))}>
                  <option value="">Select prompt...</option>
                  {prompts.map((p: any, idx: number) => (
                    <option key={p.id || p.prompt_id || idx} value={p.id || p.prompt_id || idx}>{p.name || p.title}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Metric</label>
              <select value={abTestForm.metric} onChange={e => setABTestForm(f => ({ ...f, metric: e.target.value }))}>
                {['quality', 'latency', 'cost', 'accuracy', 'relevance'].map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleCreateABTest}>Create A/B Test</button>
          </div>
        </div>
      )}

      {/* Optimize */}
      {activeSection === 'optimize' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Optimize Prompt</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group" style={{ flex: 2 }}>
                <label>Prompt ID</label>
                <select value={optimizeForm.prompt_id} onChange={e => setOptimizeForm(f => ({ ...f, prompt_id: e.target.value }))}>
                  <option value="">Select prompt...</option>
                  {prompts.map((p: any, idx: number) => (
                    <option key={p.id || p.prompt_id || idx} value={p.id || p.prompt_id || idx}>{p.name || p.title}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select value={optimizeForm.strategy} onChange={e => setOptimizeForm(f => ({ ...f, strategy: e.target.value }))}>
                  {['clarity', 'conciseness', 'specificity', 'structure', 'tone'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleOptimize}>Optimize</button>
          </div>
          {optimizeResult && (
            <div style={{ padding: 16, background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Optimization Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', color: themeColors.text, background: '#fff', padding: 12, borderRadius: 6, marginTop: 8 }}>
                {typeof optimizeResult === 'string' ? optimizeResult : JSON.stringify(optimizeResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Chain */}
      {activeSection === 'chain' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Prompt Chain</h3>
          <div className="skill-execute" style={{ marginBottom: 24, position: 'static' }}>
            <div className="form-group">
              <label>Chain Name</label>
              <input type="text" value={chainForm.name}
                onChange={e => setChainForm(f => ({ ...f, name: e.target.value }))}
                placeholder="document-analysis-pipeline" />
            </div>
            <div className="form-group">
              <label>Description</label>
              <input type="text" value={chainForm.description}
                onChange={e => setChainForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Analyze document step by step" />
            </div>
            <div className="form-group">
              <label>Steps (comma-separated prompt IDs)</label>
              <input type="text" value={chainForm.steps}
                onChange={e => setChainForm(f => ({ ...f, steps: e.target.value }))}
                placeholder="prompt-id-1, prompt-id-2, prompt-id-3" />
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleCreateChain}>Create Chain</button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Execute Chain</h3>
          <div className="skill-execute" style={{ position: 'static' }}>
            <div className="form-group">
              <label>Chain ID</label>
              <input type="text" value={executeChainForm.chain_id}
                onChange={e => setExecuteChainForm(f => ({ ...f, chain_id: e.target.value }))}
                placeholder="chain-123" />
            </div>
            <div className="form-group">
              <label>Variables (key=value, comma-separated)</label>
              <input type="text" value={executeChainForm.variables}
                onChange={e => setExecuteChainForm(f => ({ ...f, variables: e.target.value }))}
                placeholder="topic=science, length=short" />
            </div>
            <button className="btn-primary" style={{ background: themeColors.primary }} onClick={handleExecuteChain}>Execute Chain</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PromptStudioPanel;