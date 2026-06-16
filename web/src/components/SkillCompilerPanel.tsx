import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  status: string;
  parameters: string[];
  usage_count: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_tokens: number;
  avg_latency_ms: number;
  validation_score: number;
  tags: string[];
  created_at: string;
}

interface Pipeline {
  id: string;
  name: string;
  description: string;
  skills: string[];
  usage_count: number;
  success_count: number;
  success_rate: number;
  created_at: string;
}

interface SkillStats {
  total_skills: number;
  total_pipelines: number;
  total_skills_created: number;
  total_skills_improved: number;
  skills_by_status: Record<string, number>;
  skills_by_category: Record<string, number>;
  total_usage: number;
  total_success: number;
}

export const SkillCompilerPanel: React.FC = () => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [stats, setStats] = useState<SkillStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'skills' | 'pipelines' | 'stats' | 'search'>('skills');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Skill[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [skillsData, pipelinesData, statsData] = await Promise.all([
        api.skillCompiler.listSkills(selectedCategory || undefined, selectedStatus || undefined),
        api.skillCompiler.listPipelines(),
        api.skillCompiler.stats(),
      ]);
      setSkills(skillsData.skills || []);
      setPipelines(pipelinesData.pipelines || []);
      setStats(statsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load skill data');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedStatus]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      setLoading(true);
      const data = await api.skillCompiler.search(searchQuery);
      setSearchResults(data.skills || []);
      setActiveSection('search');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async (skillId: string) => {
    try {
      await api.skillCompiler.activate(skillId);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to activate skill');
    }
  };

  const handleImprove = async (skillId: string) => {
    try {
      await api.skillCompiler.improve(skillId);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to improve skill');
    }
  };

  const handleCreatePipeline = async () => {
    const selectedIds = skills.filter(s => s.status === 'active').map(s => s.id).slice(0, 3);
    if (selectedIds.length < 2) {
      setError('Need at least 2 active skills to create a pipeline');
      return;
    }
    try {
      await api.skillCompiler.createPipeline(`Pipeline-${Date.now()}`, selectedIds);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create pipeline');
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return '#10b981';
      case 'draft': return '#f59e0b';
      case 'testing': return '#3b82f6';
      case 'deprecated': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const categoryColor = (cat: string) => {
    const colors: Record<string, string> = {
      analysis: '#8b5cf6', generation: '#ec4899', transformation: '#f97316',
      integration: '#06b6d4', utility: '#6b7280', coding: '#3b82f6',
      research: '#10b981', communication: '#f59e0b',
    };
    return colors[cat] || '#6b7280';
  };

  if (loading && !stats) {
    return <div className="panel-loading">Loading skill compiler...</div>;
  }

  return (
    <div className="skill-compiler-panel">
      <div className="panel-header">
        <h2>Skill Compiler</h2>
        <div className="panel-header-actions">
          <button
            className={`btn btn-sm ${activeSection === 'skills' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('skills')}
          >
            Skills
          </button>
          <button
            className={`btn btn-sm ${activeSection === 'pipelines' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('pipelines')}
          >
            Pipelines
          </button>
          <button
            className={`btn btn-sm ${activeSection === 'stats' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('stats')}
          >
            Analytics
          </button>
          <button
            className={`btn btn-sm ${activeSection === 'search' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection('search')}
          >
            Search
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {/* Skills Section */}
      {activeSection === 'skills' && (
        <div>
          <div className="filter-bar">
            <select value={selectedCategory} onChange={e => setSelectedCategory(e.target.value)}>
              <option value="">All Categories</option>
              <option value="analysis">Analysis</option>
              <option value="generation">Generation</option>
              <option value="transformation">Transformation</option>
              <option value="integration">Integration</option>
              <option value="utility">Utility</option>
              <option value="coding">Coding</option>
              <option value="research">Research</option>
              <option value="communication">Communication</option>
            </select>
            <select value={selectedStatus} onChange={e => setSelectedStatus(e.target.value)}>
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="draft">Draft</option>
              <option value="testing">Testing</option>
              <option value="deprecated">Deprecated</option>
            </select>
            <button className="btn btn-sm btn-primary" onClick={handleCreatePipeline}>
              + Create Pipeline
            </button>
          </div>

          {skills.length === 0 ? (
            <div className="panel-empty">No skills compiled yet. Skills are auto-created from agent execution patterns.</div>
          ) : (
            <div className="skills-grid">
              {skills.map((skill) => (
                <div key={skill.id} className="skill-card">
                  <div className="skill-card-header">
                    <h4>{skill.name}</h4>
                    <span className="status-badge" style={{ background: statusColor(skill.status) }}>
                      {skill.status}
                    </span>
                  </div>
                  <div className="skill-card-meta">
                    <span className="badge" style={{ background: categoryColor(skill.category) }}>
                      {skill.category}
                    </span>
                    <span className="text-muted">v{skill.version}</span>
                  </div>
                  <p className="skill-description">{skill.description}</p>
                  <div className="skill-params">
                    {skill.parameters.map(p => (
                      <span key={p} className="param-tag">{`{${p}}`}</span>
                    ))}
                  </div>
                  <div className="skill-metrics">
                    <div className="metric">
                      <span className="metric-value">{skill.usage_count}</span>
                      <span className="metric-label">uses</span>
                    </div>
                    <div className="metric">
                      <span className="metric-value" style={{ color: '#10b981' }}>{skill.success_rate}%</span>
                      <span className="metric-label">success</span>
                    </div>
                    <div className="metric">
                      <span className="metric-value">{skill.avg_tokens}</span>
                      <span className="metric-label">avg tokens</span>
                    </div>
                  </div>
                  <div className="skill-tags">
                    {skill.tags.map(tag => (
                      <span key={tag} className="tag">{tag}</span>
                    ))}
                  </div>
                  <div className="skill-actions">
                    {skill.status === 'draft' && (
                      <button className="btn btn-xs btn-success" onClick={() => handleActivate(skill.id)}>
                        Activate
                      </button>
                    )}
                    {skill.status === 'active' && skill.usage_count > 10 && (
                      <button className="btn btn-xs btn-primary" onClick={() => handleImprove(skill.id)}>
                        Improve
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pipelines Section */}
      {activeSection === 'pipelines' && (
        <div>
          {pipelines.length === 0 ? (
            <div className="panel-empty">No pipelines created yet. Pipelines chain multiple skills together.</div>
          ) : (
            <div className="pipeline-list">
              {pipelines.map((pipeline) => (
                <div key={pipeline.id} className="pipeline-card">
                  <div className="pipeline-header">
                    <h4>{pipeline.name}</h4>
                    <span className="text-muted">{pipeline.usage_count} uses</span>
                  </div>
                  <p>{pipeline.description}</p>
                  <div className="pipeline-chain">
                    {pipeline.skills.map((sid, i) => {
                      const skill = skills.find(s => s.id === sid);
                      return (
                        <React.Fragment key={sid}>
                          {i > 0 && <span className="chain-arrow">→</span>}
                          <span className="chain-skill">
                            {skill?.name || sid.slice(0, 8)}
                          </span>
                        </React.Fragment>
                      );
                    })}
                  </div>
                  <div className="pipeline-metrics">
                    <span>Success rate: {pipeline.success_rate}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Analytics Section */}
      {activeSection === 'stats' && stats && (
        <div className="stats-section">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_skills}</div>
              <div className="stat-label">Total Skills</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_pipelines}</div>
              <div className="stat-label">Pipelines</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_skills_created}</div>
              <div className="stat-label">Created</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_skills_improved}</div>
              <div className="stat-label">Improved</div>
            </div>
          </div>

          <div className="section">
            <h4>By Status</h4>
            {Object.entries(stats.skills_by_status).map(([status, count]) => (
              <div key={status} className="metric-row">
                <span className="status-badge" style={{ background: statusColor(status) }}>{status}</span>
                <span>{count}</span>
              </div>
            ))}
          </div>

          <div className="section">
            <h4>By Category</h4>
            {Object.entries(stats.skills_by_category).map(([cat, count]) => (
              <div key={cat} className="metric-row">
                <span className="badge" style={{ background: categoryColor(cat) }}>{cat}</span>
                <span>{count}</span>
              </div>
            ))}
          </div>

          <div className="stats-grid" style={{ marginTop: '1rem' }}>
            <div className="stat-card">
              <div className="stat-value">{stats.total_usage.toLocaleString()}</div>
              <div className="stat-label">Total Usage</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_success.toLocaleString()}</div>
              <div className="stat-label">Total Success</div>
            </div>
          </div>
        </div>
      )}

      {/* Search Section */}
      {activeSection === 'search' && (
        <div>
          <div className="search-bar">
            <input
              type="text"
              placeholder="Search skills by name, description, or tags..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button className="btn btn-primary" onClick={handleSearch}>Search</button>
          </div>
          {searchResults.length === 0 ? (
            <div className="panel-empty">Enter a query to search for relevant skills.</div>
          ) : (
            <div className="skills-grid">
              {searchResults.map((skill) => (
                <div key={skill.id} className="skill-card">
                  <div className="skill-card-header">
                    <h4>{skill.name}</h4>
                    <span className="status-badge" style={{ background: statusColor(skill.status) }}>
                      {skill.status}
                    </span>
                  </div>
                  <p className="skill-description">{skill.description}</p>
                  <div className="skill-metrics">
                    <div className="metric">
                      <span className="metric-value">{skill.usage_count}</span>
                      <span className="metric-label">uses</span>
                    </div>
                    <div className="metric">
                      <span className="metric-value">{skill.success_rate}%</span>
                      <span className="metric-label">success</span>
                    </div>
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