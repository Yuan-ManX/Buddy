import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

interface CompoundedSkill {
  skill_id: string;
  name: string;
  description: string;
  category: string;
  quality_score: number;
  usage_count: number;
  success_rate: number;
  status: string;
  tags: string[];
  created_at: string;
  last_used_at: string;
}

interface InteractionPattern {
  pattern_id: string;
  description: string;
  tool_sequence: string[];
  frequency: number;
  confidence: number;
}

interface CompoundingStats {
  total_skills: number;
  active_skills: number;
  deprecated_skills: number;
  total_interactions: number;
  skills_generated: number;
  quality_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
}

const CATEGORY_EMOJIS: Record<string, string> = {
  code_generation: '💻',
  data_analysis: '📊',
  content_creation: '📝',
  automation: '🤖',
  debugging: '🐛',
  testing: '🧪',
  documentation: '📖',
  general: '🔧',
};

export const CompoundingPanel: React.FC = () => {
  const [skills, setSkills] = useState<CompoundedSkill[]>([]);
  const [patterns, setPatterns] = useState<InteractionPattern[]>([]);
  const [stats, setStats] = useState<CompoundingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSkill, setSelectedSkill] = useState<CompoundedSkill | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);
  const [generating, setGenerating] = useState(false);
  const { success: showSuccess, error: showError } = useToast();

  useEffect(() => {
    loadData();
  }, [categoryFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [skillsRes, patternsRes, statsRes] = await Promise.all([
        api.compounding.listSkills(categoryFilter || undefined),
        api.compounding.getPatterns(),
        api.compounding.stats(),
      ]);
      setSkills(skillsRes.skills as unknown as CompoundedSkill[]);
      setPatterns(patternsRes.patterns as unknown as InteractionPattern[]);
      setStats(statsRes as unknown as CompoundingStats);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load compounding data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSkills = async () => {
    try {
      setGenerating(true);
      const res = await api.compounding.generateSkills();
      const newSkills = res.skills as unknown as CompoundedSkill[];
      showSuccess(`Generated ${newSkills.length} new compound skills`);
      loadData();
    } catch (e: any) {
      showError('Failed to generate skills');
    } finally {
      setGenerating(false);
      setShowGenerate(false);
    }
  };

  const handleFeedback = async (skill: CompoundedSkill, success: boolean) => {
    try {
      await api.compounding.feedback(skill.skill_id, success);
      showSuccess(`Feedback recorded for "${skill.name}"`);
      loadData();
    } catch (e: any) {
      showError('Failed to record feedback');
    }
  };

  const handleDeprecate = async (skill: CompoundedSkill) => {
    if (!confirm(`Deprecate skill "${skill.name}"?`)) return;
    try {
      await api.compounding.deprecateSkill(skill.skill_id);
      showSuccess(`Deprecated "${skill.name}"`);
      loadData();
    } catch (e: any) {
      showError('Failed to deprecate skill');
    }
  };

  const handleDelete = async (skill: CompoundedSkill) => {
    if (!confirm(`Permanently delete skill "${skill.name}"?`)) return;
    try {
      await api.compounding.deleteSkill(skill.skill_id);
      showSuccess(`Deleted "${skill.name}"`);
      loadData();
    } catch (e: any) {
      showError('Failed to delete skill');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadData();
      return;
    }
    try {
      const res = await api.compounding.searchSkills(searchQuery);
      setSkills(res.skills as unknown as CompoundedSkill[]);
    } catch (e: any) {
      showError('Search failed');
    }
  };

  const filteredSkills = skills.filter(s =>
    !searchQuery.trim() ||
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading && !skills.length) {
    return <div className="panel-loading">Loading compounding data...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Skill Compounding</h2>
        <div className="panel-header-actions">
          <button className="btn-primary" onClick={() => setShowGenerate(true)}>
            ⚡ Generate Skills
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="board-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_skills}</span>
            <span className="stat-label">Total Skills</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.active_skills || stats.total_skills}</span>
            <span className="stat-label">Active</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_interactions}</span>
            <span className="stat-label">Interactions</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.skills_generated || 0}</span>
            <span className="stat-label">Generated</span>
          </div>
        </div>
      )}

      <div className="search-bar">
        <input
          type="text"
          placeholder="Search skills..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn-secondary" onClick={handleSearch}>Search</button>
      </div>

      <div className="compounding-grid">
        {/* Skills List */}
        <div className="compounding-column">
          <h3>Compound Skills</h3>
          {filteredSkills.map(skill => (
            <div
              key={skill.skill_id}
              className={`compound-card ${selectedSkill?.skill_id === skill.skill_id ? 'selected' : ''} ${skill.status === 'deprecated' ? 'deprecated' : ''}`}
              onClick={() => setSelectedSkill(skill)}
            >
              <div className="compound-card-header">
                <span className="category-emoji">
                  {CATEGORY_EMOJIS[skill.category] || '🔧'}
                </span>
                <div>
                  <h4>{skill.name}</h4>
                  <span className="compound-category">{skill.category}</span>
                </div>
                <span className={`status-badge ${skill.status}`}>
                  {skill.status}
                </span>
              </div>
              <p className="compound-description">{skill.description}</p>
              <div className="compound-metrics">
                <span title="Quality Score">⭐ {skill.quality_score?.toFixed(2) || 'N/A'}</span>
                <span title="Usage Count">🔄 {skill.usage_count || 0}</span>
                <span title="Success Rate">✅ {((skill.success_rate || 0) * 100).toFixed(0)}%</span>
              </div>
              {skill.tags?.length > 0 && (
                <div className="tag-list">
                  {skill.tags.map((tag, idx) => (
                    <span key={idx} className="tag">{tag}</span>
                  ))}
                </div>
              )}
              <div className="compound-card-actions">
                <button
                  className="btn-sm btn-success"
                  onClick={(e) => { e.stopPropagation(); handleFeedback(skill, true); }}
                  title="Thumbs up"
                >
                  👍
                </button>
                <button
                  className="btn-sm btn-danger"
                  onClick={(e) => { e.stopPropagation(); handleFeedback(skill, false); }}
                  title="Thumbs down"
                >
                  👎
                </button>
                {skill.status !== 'deprecated' && (
                  <button
                    className="btn-sm btn-secondary"
                    onClick={(e) => { e.stopPropagation(); handleDeprecate(skill); }}
                  >
                    Deprecate
                  </button>
                )}
                <button
                  className="btn-sm btn-danger"
                  onClick={(e) => { e.stopPropagation(); handleDelete(skill); }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          {filteredSkills.length === 0 && (
            <div className="panel-empty">No compound skills. Generate or import some to get started.</div>
          )}
        </div>

        {/* Patterns Panel */}
        <div className="compounding-column">
          <h3>Interaction Patterns</h3>
          {patterns.map(pattern => (
            <div key={pattern.pattern_id} className="pattern-card">
              <div className="pattern-header">
                <span className="pattern-frequency">📊 {pattern.frequency}x</span>
                <span className="pattern-confidence" title="Confidence">
                  {((pattern.confidence || 0) * 100).toFixed(0)}% confidence
                </span>
              </div>
              <p className="pattern-description">{pattern.description}</p>
              {pattern.tool_sequence?.length > 0 && (
                <div className="tool-sequence">
                  {pattern.tool_sequence.map((tool, idx) => (
                    <span key={idx} className="tool-step">
                      {idx > 0 && <span className="tool-arrow">→</span>}
                      <code>{tool}</code>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {patterns.length === 0 && (
            <div className="panel-empty">No patterns detected yet. Record interactions to discover patterns.</div>
          )}
        </div>
      </div>

      {/* Generate Skills Modal */}
      {showGenerate && (
        <div className="modal-overlay" onClick={() => setShowGenerate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Generate Compound Skills</h2>
            <p className="modal-help">
              The compounding engine will analyze interaction patterns and generate new compound skills by combining successful tool sequences.
            </p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowGenerate(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleGenerateSkills} disabled={generating}>
                {generating ? 'Generating...' : 'Generate Skills'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};