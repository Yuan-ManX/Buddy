import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

interface SkillFabricStats {
  forge: { total_skills: number; by_type: Record<string, number>; by_lifecycle: Record<string, number> };
  bundles: { total_bundles: number; avg_skills_per_bundle: number };
  market: { total_listed: number; featured: number; avg_rating: number; total_downloads: number };
  composer: { total_compositions: number; by_mode: Record<string, number> };
  analytics: any;
}

interface SkillItem {
  skill_id: string;
  name: string;
  skill_type: string;
  lifecycle: string;
  version: string;
}

interface MarketSkill {
  skill_id: string;
  name: string;
  skill_type: string;
  pricing: string;
  rating: number;
}

export const SkillFabricPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<SkillFabricStats | null>(null);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [marketSkills, setMarketSkills] = useState<MarketSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'bundle' | 'compose' | 'market'>('overview');

  // Create form
  const [createForm, setCreateForm] = useState({
    name: '',
    skill_type: 'tool_chain',
    description: '',
    steps: '',
    preconditions: '',
    postconditions: '',
    created_by: '',
  });

  // Bundle form
  const [bundleForm, setBundleForm] = useState({
    name: '',
    description: '',
    skill_ids: '',
    created_by: '',
  });

  // Compose form
  const [composeForm, setComposeForm] = useState({
    skill_ids: '',
    mode: 'sequential',
    input_mapping: '',
  });
  const [composeResult, setComposeResult] = useState<any>(null);

  // Market search
  const [marketQuery, setMarketQuery] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsRes, listRes, marketRes] = await Promise.all([
        fetch('/api/skill-fabric/stats'),
        fetch('/api/skill-fabric/list'),
        fetch('/api/skill-fabric/market'),
      ]);
      const s = await statsRes.json();
      const l = await listRes.json();
      const m = await marketRes.json();
      setStats(s);
      setSkills(l.skills || []);
      setMarketSkills(m.skills || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async () => {
    try {
      let steps = [];
      let preconditions = [];
      let postconditions = [];
      try { steps = JSON.parse(createForm.steps || '[]'); } catch {}
      try { preconditions = JSON.parse(createForm.preconditions || '[]'); } catch {}
      try { postconditions = JSON.parse(createForm.postconditions || '[]'); } catch {}
      const res = await fetch('/api/skill-fabric/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...createForm, steps, preconditions, postconditions }),
      });
      const data = await res.json();
      toast?.success?.('Skill created: ' + data.skill_id);
      setCreateForm({ name: '', skill_type: 'tool_chain', description: '', steps: '', preconditions: '', postconditions: '', created_by: '' });
      loadData();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleCreateBundle = async () => {
    try {
      const res = await fetch('/api/skill-fabric/bundle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...bundleForm,
          skill_ids: bundleForm.skill_ids ? bundleForm.skill_ids.split(',').map(s => s.trim()) : [],
        }),
      });
      const data = await res.json();
      toast?.success?.('Bundle created: ' + data.bundle_id);
      setBundleForm({ name: '', description: '', skill_ids: '', created_by: '' });
      loadData();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleCompose = async () => {
    try {
      let inputMapping = {};
      try { inputMapping = JSON.parse(composeForm.input_mapping || '{}'); } catch {}
      const res = await fetch('/api/skill-fabric/compose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_ids: composeForm.skill_ids ? composeForm.skill_ids.split(',').map(s => s.trim()) : [],
          mode: composeForm.mode,
          input_mapping: inputMapping,
        }),
      });
      const data = await res.json();
      setComposeResult(data);
      loadData();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleMarketSearch = async () => {
    try {
      const res = await fetch(`/api/skill-fabric/market?query=${encodeURIComponent(marketQuery)}`);
      const data = await res.json();
      setMarketSkills(data.skills || []);
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  if (loading) return <div className="panel loading">Loading skill fabric...</div>;

  return (
    <div className="panel skill-fabric-panel">
      <div className="panel-header">
        <h2>Skill Fabric</h2>
        <span className="panel-badge">
          {stats ? `${stats.forge?.total_skills || 0} skills` : 'Loading'}
        </span>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-tabs">
        {(['overview', 'create', 'bundle', 'compose', 'market'] as const).map((s) => (
          <button
            key={s}
            className={`panel-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="panel-content">
        {activeSection === 'overview' && stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.forge?.total_skills || 0}</div>
              <div className="stat-label">Total Skills</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.bundles?.total_bundles || 0}</div>
              <div className="stat-label">Bundles</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.market?.total_listed || 0}</div>
              <div className="stat-label">Market Listings</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.market?.avg_rating?.toFixed(1) || '0.0'}</div>
              <div className="stat-label">Avg Rating</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.composer?.total_compositions || 0}</div>
              <div className="stat-label">Compositions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.market?.total_downloads || 0}</div>
              <div className="stat-label">Downloads</div>
            </div>

            {stats.forge?.by_type && (
              <div className="section-card full-width">
                <h3>Skill Types</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.forge.by_type).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.forge.by_type).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.forge?.by_lifecycle && (
              <div className="section-card full-width">
                <h3>Lifecycle Distribution</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.forge.by_lifecycle).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.forge.by_lifecycle).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'create' && (
          <div className="form-section">
            <h3>Create Skill</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Name</label>
                <input type="text" value={createForm.name} onChange={e => setCreateForm({ ...createForm, name: e.target.value })} placeholder="My Skill" />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={createForm.skill_type} onChange={e => setCreateForm({ ...createForm, skill_type: e.target.value })}>
                  <option value="tool_chain">Tool Chain</option>
                  <option value="prompt_template">Prompt Template</option>
                  <option value="workflow">Workflow</option>
                  <option value="code_executor">Code Executor</option>
                  <option value="data_processor">Data Processor</option>
                </select>
              </div>
              <div className="form-group">
                <label>Created By</label>
                <input type="text" value={createForm.created_by} onChange={e => setCreateForm({ ...createForm, created_by: e.target.value })} placeholder="agent-..." />
              </div>
              <div className="form-group full-width">
                <label>Description</label>
                <textarea value={createForm.description} onChange={e => setCreateForm({ ...createForm, description: e.target.value })} placeholder="What does this skill do?" rows={2} />
              </div>
              <div className="form-group full-width">
                <label>Steps (JSON array)</label>
                <textarea value={createForm.steps} onChange={e => setCreateForm({ ...createForm, steps: e.target.value })} placeholder='[{"action": "do_something"}]' rows={2} />
              </div>
              <div className="form-group">
                <label>Preconditions (JSON array)</label>
                <textarea value={createForm.preconditions} onChange={e => setCreateForm({ ...createForm, preconditions: e.target.value })} placeholder='["cond1", "cond2"]' rows={2} />
              </div>
              <div className="form-group">
                <label>Postconditions (JSON array)</label>
                <textarea value={createForm.postconditions} onChange={e => setCreateForm({ ...createForm, postconditions: e.target.value })} placeholder='["result1", "result2"]' rows={2} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleCreate}>Create Skill</button>
          </div>
        )}

        {activeSection === 'bundle' && (
          <div className="form-section">
            <h3>Create Skill Bundle</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Bundle Name</label>
                <input type="text" value={bundleForm.name} onChange={e => setBundleForm({ ...bundleForm, name: e.target.value })} placeholder="My Bundle" />
              </div>
              <div className="form-group">
                <label>Created By</label>
                <input type="text" value={bundleForm.created_by} onChange={e => setBundleForm({ ...bundleForm, created_by: e.target.value })} placeholder="agent-..." />
              </div>
              <div className="form-group full-width">
                <label>Description</label>
                <textarea value={bundleForm.description} onChange={e => setBundleForm({ ...bundleForm, description: e.target.value })} placeholder="Bundle description..." rows={2} />
              </div>
              <div className="form-group full-width">
                <label>Skill IDs (comma-separated)</label>
                <textarea value={bundleForm.skill_ids} onChange={e => setBundleForm({ ...bundleForm, skill_ids: e.target.value })} placeholder="skill-001, skill-002" rows={2} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleCreateBundle}>Create Bundle</button>

            {skills.length > 0 && (
              <div className="section-card" style={{ marginTop: '1rem' }}>
                <h4>Available Skills</h4>
                <div className="room-list">
                  {skills.map(s => (
                    <div key={s.skill_id} className="room-card" style={{ cursor: 'pointer' }} onClick={() => {
                      const current = bundleForm.skill_ids ? bundleForm.skill_ids.split(',').map(x => x.trim()) : [];
                      if (!current.includes(s.skill_id)) {
                        setBundleForm({ ...bundleForm, skill_ids: [...current, s.skill_id].join(', ') });
                      }
                    }}>
                      <div className="room-name">{s.name}</div>
                      <div className="room-meta">
                        <span className="room-type-badge">{s.skill_type}</span>
                        <span className="room-state-badge">{s.lifecycle}</span>
                        <span>v{s.version}</span>
                      </div>
                      <div className="room-id">ID: {s.skill_id}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'compose' && (
          <div className="form-section">
            <h3>Compose Skills into Workflow</h3>
            <div className="form-grid">
              <div className="form-group full-width">
                <label>Skill IDs (comma-separated)</label>
                <input type="text" value={composeForm.skill_ids} onChange={e => setComposeForm({ ...composeForm, skill_ids: e.target.value })} placeholder="skill-001, skill-002" />
              </div>
              <div className="form-group">
                <label>Mode</label>
                <select value={composeForm.mode} onChange={e => setComposeForm({ ...composeForm, mode: e.target.value })}>
                  <option value="sequential">Sequential</option>
                  <option value="parallel">Parallel</option>
                  <option value="conditional">Conditional</option>
                  <option value="pipeline">Pipeline</option>
                </select>
              </div>
              <div className="form-group full-width">
                <label>Input Mapping (JSON)</label>
                <textarea value={composeForm.input_mapping} onChange={e => setComposeForm({ ...composeForm, input_mapping: e.target.value })} placeholder='{"skill-001": {"input": "value"}}' rows={2} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleCompose}>Compose</button>
            {composeResult && (
              <div className="result-card" style={{ marginTop: '1rem' }}>
                <div className="result-meta">
                  <span>Plan: {composeResult.plan_id}</span>
                  <span>Mode: {composeResult.mode}</span>
                  <span>Steps: {composeResult.steps?.length || 0}</span>
                </div>
                <pre>{JSON.stringify(composeResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeSection === 'market' && (
          <div className="section-card">
            <h3>Skill Marketplace</h3>
            <div className="form-row" style={{ marginBottom: '1rem' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <input type="text" value={marketQuery} onChange={e => setMarketQuery(e.target.value)} placeholder="Search skills..." onKeyDown={e => e.key === 'Enter' && handleMarketSearch()} />
              </div>
              <button className="btn-primary" onClick={handleMarketSearch}>Search</button>
            </div>
            {marketSkills.length === 0 ? (
              <p className="empty-text">No skills found in marketplace.</p>
            ) : (
              <div className="room-list">
                {marketSkills.map(s => (
                  <div key={s.skill_id} className="room-card">
                    <div className="room-name">{s.name}</div>
                    <div className="room-meta">
                      <span className="room-type-badge">{s.skill_type}</span>
                      <span className="room-state-badge">{s.pricing}</span>
                      <span>Rating: {s.rating != null ? s.rating.toFixed(1) : 'N/A'}</span>
                    </div>
                    <div className="room-id">ID: {s.skill_id}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};