import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../api/client';

interface ManagedSkill {
  skill_id: string;
  name: string;
  description: string;
  category: string;
  status: string;
  tags: string[];
  versions: Array<{
    version: number;
    prompt_template: string;
    parameters: Array<{ name: string; type: string; description: string; required: boolean }>;
    created_at: string;
    success_rate: number;
    execution_count: number;
    avg_tokens: number;
    avg_latency_ms: number;
  }>;
  parent_skill_id: string;
  author_agent_id: string;
  created_at: string;
  updated_at: string;
  total_executions: number;
  average_rating: number;
  latest_success_rate: number;
}

interface SkillFormData {
  name: string;
  description: string;
  category: string;
  prompt_template: string;
  parameters: Array<{ name: string; type: string; description: string; required: boolean }>;
  tags: string[];
  author_agent_id: string;
}

const CATEGORIES = ['reasoning', 'coding', 'data', 'communication', 'automation', 'research', 'creative', 'custom'];
const EMPTY_FORM: SkillFormData = {
  name: '',
  description: '',
  category: 'custom',
  prompt_template: '',
  parameters: [],
  tags: [],
  author_agent_id: '',
};

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString();
}

export const SkillManager: React.FC = () => {
  const [skills, setSkills] = useState<ManagedSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showCreate, setShowCreate] = useState(false);
  const [editingSkill, setEditingSkill] = useState<ManagedSkill | null>(null);
  const [formData, setFormData] = useState<SkillFormData>(EMPTY_FORM);
  const [newParam, setNewParam] = useState({ name: '', type: 'string', description: '', required: false });
  const [newTag, setNewTag] = useState('');
  const [stats, setStats] = useState<{ total_skills: number; total_executions: number; avg_success_rate: number } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchSkills = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [skillsRes, statsRes] = await Promise.all([
        api.forge.skills(),
        api.forge.stats(),
      ]);
      setSkills(skillsRes as unknown as ManagedSkill[]);
      setStats(statsRes as unknown as { total_skills: number; total_executions: number; avg_success_rate: number });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load skills');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const filteredSkills = useMemo(() => {
    return skills.filter(s => {
      if (search && !s.name.toLowerCase().includes(search.toLowerCase()) &&
          !s.description.toLowerCase().includes(search.toLowerCase())) return false;
      if (filterCategory && s.category !== filterCategory) return false;
      if (filterStatus && s.status !== filterStatus) return false;
      return true;
    });
  }, [skills, search, filterCategory, filterStatus]);

  const handleCreate = async () => {
    if (!formData.name.trim() || !formData.description.trim()) return;
    try {
      await api.forge.create({
        name: formData.name,
        description: formData.description,
        category: formData.category,
        prompt_template: formData.prompt_template,
        parameters: formData.parameters,
        author_agent_id: formData.author_agent_id || undefined,
        tags: formData.tags,
      });
      setShowCreate(false);
      setFormData(EMPTY_FORM);
      fetchSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create skill');
    }
  };

  const handleUpdate = async () => {
    if (!editingSkill || !formData.name.trim()) return;
    try {
      await api.forge.evolve(editingSkill.skill_id, formData.prompt_template);
      setEditingSkill(null);
      setFormData(EMPTY_FORM);
      fetchSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update skill');
    }
  };

  const handleDelete = async (skillId: string) => {
    try {
      await api.forge.archive(skillId);
      setDeleteConfirm(null);
      fetchSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete skill');
    }
  };

  const handleToggleStatus = async (skill: ManagedSkill) => {
    try {
      if (skill.status === 'active') {
        await api.forge.deprecate(skill.skill_id);
      } else {
        // Re-activate by re-creating (simplified — in reality might need a dedicated endpoint)
        fetchSkills();
      }
      fetchSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle skill status');
    }
  };

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(filteredSkills, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'buddy-skills.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const importedSkills = JSON.parse(text);
        if (!Array.isArray(importedSkills)) throw new Error('Invalid format: expected an array of skills');
        let imported = 0;
        for (const skill of importedSkills) {
          if (skill.name && skill.description && skill.prompt_template) {
            try {
              await api.forge.create({
                name: skill.name,
                description: skill.description,
                category: skill.category || 'custom',
                prompt_template: skill.prompt_template,
                parameters: skill.parameters || [],
                tags: skill.tags || [],
              });
              imported++;
            } catch {}
          }
        }
        setError(null);
        fetchSkills();
        if (imported > 0) {
          setError(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to import skills');
      }
    };
    input.click();
  };

  const handleAddParam = () => {
    if (!newParam.name.trim()) return;
    setFormData(prev => ({
      ...prev,
      parameters: [...prev.parameters, { ...newParam }],
    }));
    setNewParam({ name: '', type: 'string', description: '', required: false });
  };

  const handleRemoveParam = (index: number) => {
    setFormData(prev => ({
      ...prev,
      parameters: prev.parameters.filter((_, i) => i !== index),
    }));
  };

  const handleAddTag = () => {
    if (!newTag.trim()) return;
    setFormData(prev => ({
      ...prev,
      tags: [...prev.tags, newTag.trim()],
    }));
    setNewTag('');
  };

  const handleRemoveTag = (tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag),
    }));
  };

  const openEdit = (skill: ManagedSkill) => {
    const latestVersion = skill.versions[skill.versions.length - 1];
    setEditingSkill(skill);
    setFormData({
      name: skill.name,
      description: skill.description,
      category: skill.category,
      prompt_template: latestVersion?.prompt_template || '',
      parameters: latestVersion?.parameters || [],
      tags: skill.tags || [],
      author_agent_id: skill.author_agent_id || '',
    });
  };

  const openCreate = () => {
    setEditingSkill(null);
    setFormData(EMPTY_FORM);
    setShowCreate(true);
  };

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Skill Manager</h2>
          <p className="panel-subtitle">Create, manage, and monitor agent skills</p>
        </div>
        <div className="panel-header-actions">
          <button className="btn-sm" onClick={handleExport}>Export</button>
          <button className="btn-sm" onClick={handleImport}>Import</button>
          <button className="btn-primary" onClick={openCreate}>Create Skill</button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="btn-sm" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="skillmanager-stats-grid">
          <div className="skillmanager-stat-card">
            <span className="skillmanager-stat-value">{stats.total_skills}</span>
            <span className="skillmanager-stat-label">Total Skills</span>
          </div>
          <div className="skillmanager-stat-card">
            <span className="skillmanager-stat-value">{stats.total_executions}</span>
            <span className="skillmanager-stat-label">Executions</span>
          </div>
          <div className="skillmanager-stat-card">
            <span className="skillmanager-stat-value" style={{ color: stats.avg_success_rate >= 0.8 ? '#10b981' : stats.avg_success_rate >= 0.5 ? '#f59e0b' : '#ef4444' }}>
              {Math.round(stats.avg_success_rate * 100)}%
            </span>
            <span className="skillmanager-stat-label">Success Rate</span>
          </div>
        </div>
      )}

      {/* Search & Filters */}
      <div className="skillmanager-filters">
        <div className="skillmanager-search">
          <input
            className="panel-search-input"
            type="text"
            placeholder="Search skills..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="skillmanager-filter-group">
          <select
            className="filter-select"
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
          >
            <option value="">All Categories</option>
            {CATEGORIES.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            className="filter-select"
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="deprecated">Deprecated</option>
            <option value="archived">Archived</option>
          </select>
          <div className="skillmanager-view-toggle">
            <button
              className={`skillmanager-view-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid View"
            >
              ▦
            </button>
            <button
              className={`skillmanager-view-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List View"
            >
              ☰
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div className="panel-loading">Loading skills...</div>
      )}

      {!loading && filteredSkills.length === 0 && !error && (
        <div className="panel-empty skillmanager-empty">
          <div className="skillmanager-empty-icon">🧩</div>
          <p>No skills found</p>
          <span>{search || filterCategory || filterStatus ? 'Try adjusting your filters.' : 'Create your first skill to get started.'}</span>
        </div>
      )}

      {/* Skills Grid/List */}
      <div className={`skillmanager-grid ${viewMode}`}>
        {filteredSkills.map(skill => {
          const latestVersion = skill.versions[skill.versions.length - 1];
          const successRate = Math.round(skill.latest_success_rate * 100);

          return (
            <div key={skill.skill_id} className={`skillmanager-card ${skill.status}`}>
              <div className="skillmanager-card-header">
                <div className="skillmanager-card-icon">
                  {skill.category === 'reasoning' ? '🧠' :
                   skill.category === 'coding' ? '💻' :
                   skill.category === 'data' ? '📊' :
                   skill.category === 'communication' ? '💬' :
                   skill.category === 'automation' ? '⚙️' :
                   skill.category === 'research' ? '🔬' :
                   skill.category === 'creative' ? '🎨' : '📦'}
                </div>
                <div className="skillmanager-card-info">
                  <div className="skillmanager-card-name">{skill.name}</div>
                  <div className="skillmanager-card-category">{skill.category}</div>
                </div>
                <span className={`skillmanager-status-badge ${skill.status}`}>
                  {skill.status}
                </span>
              </div>
              <div className="skillmanager-card-body">
                <p className="skillmanager-card-desc">{skill.description}</p>
                {skill.tags && skill.tags.length > 0 && (
                  <div className="skillmanager-card-tags">
                    {skill.tags.map(tag => (
                      <span key={tag} className="skillmanager-tag">{tag}</span>
                    ))}
                  </div>
                )}
                <div className="skillmanager-card-metrics">
                  <span className="skillmanager-metric">
                    <span className="skillmanager-metric-label">Version</span>
                    <span className="skillmanager-metric-value">{latestVersion?.version || 1}</span>
                  </span>
                  <span className="skillmanager-metric">
                    <span className="skillmanager-metric-label">Executions</span>
                    <span className="skillmanager-metric-value">{skill.total_executions}</span>
                  </span>
                  <span className="skillmanager-metric">
                    <span className="skillmanager-metric-label">Success</span>
                    <span className="skillmanager-metric-value" style={{ color: successRate >= 80 ? '#10b981' : successRate >= 50 ? '#f59e0b' : '#ef4444' }}>
                      {successRate}%
                    </span>
                  </span>
                  <span className="skillmanager-metric">
                    <span className="skillmanager-metric-label">Last Used</span>
                    <span className="skillmanager-metric-value">{formatDate(skill.updated_at)}</span>
                  </span>
                </div>
                {latestVersion && (
                  <div className="skillmanager-card-prompt">
                    <span className="skillmanager-prompt-label">Prompt Template</span>
                    <pre className="skillmanager-prompt-text">{latestVersion.prompt_template.slice(0, 200)}{latestVersion.prompt_template.length > 200 ? '...' : ''}</pre>
                  </div>
                )}
              </div>
              <div className="skillmanager-card-actions">
                <button className="btn-sm" onClick={() => openEdit(skill)}>Edit</button>
                <button
                  className={`btn-sm ${skill.status === 'active' ? 'btn-danger' : 'btn-success'}`}
                  onClick={() => handleToggleStatus(skill)}
                >
                  {skill.status === 'active' ? 'Disable' : 'Enable'}
                </button>
                {skill.status !== 'archived' && (
                  <button
                    className="btn-sm btn-danger"
                    onClick={() => setDeleteConfirm(skill.skill_id)}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>Delete Skill</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 20, fontSize: '0.9rem' }}>
              Are you sure you want to archive this skill? This action cannot be undone.
            </p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setDeleteConfirm(null)}>Cancel</button>
              <button className="btn-primary" style={{ background: '#ef4444' }} onClick={() => handleDelete(deleteConfirm)}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit Modal */}
      {(showCreate || editingSkill) && (
        <div className="modal-overlay" onClick={() => { setShowCreate(false); setEditingSkill(null); }}>
          <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
            <h2>{editingSkill ? 'Edit Skill' : 'Create New Skill'}</h2>

            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                placeholder="Skill name"
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                autoFocus
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Category</label>
                <select
                  value={formData.category}
                  onChange={e => setFormData({ ...formData, category: e.target.value })}
                >
                  {CATEGORIES.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Author Agent ID</label>
                <input
                  type="text"
                  placeholder="Optional"
                  value={formData.author_agent_id}
                  onChange={e => setFormData({ ...formData, author_agent_id: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                placeholder="Describe what this skill does..."
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
                rows={2}
              />
            </div>

            <div className="form-group">
              <label>System Prompt Template</label>
              <textarea
                placeholder="Enter the system prompt template for this skill..."
                value={formData.prompt_template}
                onChange={e => setFormData({ ...formData, prompt_template: e.target.value })}
                rows={4}
              />
            </div>

            {/* Parameters */}
            <div className="form-group">
              <label>Parameters</label>
              <div className="skillmanager-param-list">
                {formData.parameters.map((param, i) => (
                  <div key={i} className="skillmanager-param-chip">
                    <span className="skillmanager-param-chip-name">{param.name}</span>
                    <span className="skillmanager-param-chip-type">{param.type}</span>
                    <button
                      className="skillmanager-param-chip-remove"
                      onClick={() => handleRemoveParam(i)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <div className="skillmanager-param-add">
                <input
                  className="skillmanager-param-input"
                  type="text"
                  placeholder="Param name"
                  value={newParam.name}
                  onChange={e => setNewParam({ ...newParam, name: e.target.value })}
                />
                <select
                  className="skillmanager-param-select"
                  value={newParam.type}
                  onChange={e => setNewParam({ ...newParam, type: e.target.value })}
                >
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="object">object</option>
                  <option value="array">array</option>
                </select>
                <label className="skillmanager-param-required">
                  <input
                    type="checkbox"
                    checked={newParam.required}
                    onChange={e => setNewParam({ ...newParam, required: e.target.checked })}
                  />
                  Required
                </label>
                <button className="btn-sm" onClick={handleAddParam}>Add</button>
              </div>
            </div>

            {/* Tags */}
            <div className="form-group">
              <label>Tags</label>
              <div className="skillmanager-param-list">
                {formData.tags.map(tag => (
                  <div key={tag} className="skillmanager-tag-chip">
                    <span>{tag}</span>
                    <button
                      className="skillmanager-param-chip-remove"
                      onClick={() => handleRemoveTag(tag)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <div className="skillmanager-tag-add">
                <input
                  className="skillmanager-param-input"
                  type="text"
                  placeholder="Add tag..."
                  value={newTag}
                  onChange={e => setNewTag(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAddTag(); } }}
                />
                <button className="btn-sm" onClick={handleAddTag}>Add</button>
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => { setShowCreate(false); setEditingSkill(null); }}>
                Cancel
              </button>
              <button className="btn-primary" onClick={editingSkill ? handleUpdate : handleCreate}>
                {editingSkill ? 'Save Changes' : 'Create Skill'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillManager;