import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ForgedSkill, InteractionPattern, ForgeStats } from '../types';

const CATEGORY_OPTIONS = ['utility', 'creative', 'analysis', 'engineering', 'education', 'communication', 'automation'];

export const ForgePanel: React.FC = () => {
  const [stats, setStats] = useState<ForgeStats | null>(null);
  const [skills, setSkills] = useState<ForgedSkill[]>([]);
  const [patterns, setPatterns] = useState<{ patterns: InteractionPattern[]; promotable: InteractionPattern[] }>({ patterns: [], promotable: [] });
  const [activeTab, setActiveTab] = useState<'skills' | 'patterns' | 'create'>('skills');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createCategory, setCreateCategory] = useState('utility');
  const [createPrompt, setCreatePrompt] = useState('');
  const [createTags, setCreateTags] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<ForgedSkill | null>(null);

  // Evolve modal state
  const [evolveSkillId, setEvolveSkillId] = useState<string | null>(null);
  const [evolvePrompt, setEvolvePrompt] = useState('');
  const [evolveReason, setEvolveReason] = useState('');
  const [evolveLoading, setEvolveLoading] = useState(false);

  // Promote modal state
  const [promotePattern, setPromotePattern] = useState<InteractionPattern | null>(null);
  const [promoteName, setPromoteName] = useState('');
  const [promoteDescription, setPromoteDescription] = useState('');
  const [promotePrompt, setPromotePrompt] = useState('');
  const [promoteLoading, setPromoteLoading] = useState(false);

  // Notification snackbar
  const [snackbar, setSnackbar] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showSnackbar = (message: string, type: 'success' | 'error') => {
    setSnackbar({ message, type });
    setTimeout(() => setSnackbar(null), 3000);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, skillsData, patternsData] = await Promise.all([
        api.forge.stats(),
        api.forge.skills(),
        api.forge.patterns(),
      ]);
      setStats(statsData);
      setSkills(skillsData);
      setPatterns(patternsData);
    } catch (e: any) {
      setError(e.message || 'Failed to load forge data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async () => {
    if (!createName.trim() || !createDescription.trim()) return;
    setCreateLoading(true);
    try {
      const tagsArray = createTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      await api.forge.create({
        name: createName.trim(),
        description: createDescription.trim(),
        category: createCategory,
        prompt_template: createPrompt.trim(),
        tags: tagsArray.length > 0 ? tagsArray : undefined,
      });
      setCreateName('');
      setCreateDescription('');
      setCreateCategory('utility');
      setCreatePrompt('');
      setCreateTags('');
      setShowCreateForm(false);
      showSnackbar('Skill created successfully', 'success');
      await loadData();
    } catch (e: any) {
      showSnackbar(e.message || 'Failed to create skill', 'error');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleEvolve = async (skillId: string) => {
    setEvolveLoading(true);
    try {
      await api.forge.evolve(skillId, evolvePrompt.trim(), evolveReason.trim() || undefined);
      setEvolveSkillId(null);
      setEvolvePrompt('');
      setEvolveReason('');
      showSnackbar('Skill evolved to new version', 'success');
      await loadData();
    } catch (e: any) {
      showSnackbar(e.message || 'Failed to evolve skill', 'error');
    } finally {
      setEvolveLoading(false);
    }
  };

  const handlePromote = async (pattern: InteractionPattern) => {
    setPromoteLoading(true);
    try {
      await api.forge.promote(
        pattern.pattern_id,
        promoteName.trim(),
        promoteDescription.trim(),
        promotePrompt.trim(),
      );
      setPromotePattern(null);
      setPromoteName('');
      setPromoteDescription('');
      setPromotePrompt('');
      showSnackbar('Pattern promoted to skill', 'success');
      await loadData();
    } catch (e: any) {
      showSnackbar(e.message || 'Failed to promote pattern', 'error');
    } finally {
      setPromoteLoading(false);
    }
  };

  const handleDeprecate = async (skillId: string) => {
    try {
      await api.forge.deprecate(skillId);
      showSnackbar('Skill deprecated', 'success');
      await loadData();
    } catch (e: any) {
      showSnackbar(e.message || 'Failed to deprecate skill', 'error');
    }
  };

  const handleArchive = async (skillId: string) => {
    try {
      await api.forge.archive(skillId);
      showSnackbar('Skill archived', 'success');
      await loadData();
    } catch (e: any) {
      showSnackbar(e.message || 'Failed to archive skill', 'error');
    }
  };

  const openEvolveModal = (skillId: string, currentPrompt: string) => {
    setEvolveSkillId(skillId);
    setEvolvePrompt(currentPrompt);
    setEvolveReason('');
  };

  const openPromoteModal = (pattern: InteractionPattern) => {
    setPromotePattern(pattern);
    setPromoteName(pattern.suggested_category
      ? `${pattern.suggested_category}_pattern`
      : 'new_pattern_skill');
    setPromoteDescription(pattern.description);
    setPromotePrompt(pattern.action_sequence.join('\n'));
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const statusClass = (status: string) => {
    if (status === 'active') return 'active';
    if (status === 'deprecated') return 'deprecated';
    if (status === 'archived') return 'archived';
    return '';
  };

  const percentColor = (rate: number) => {
    if (rate >= 0.8) return '#10b981';
    if (rate >= 0.5) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Buddy Forge</h2>
          <span className="panel-subtitle">Self-improving skill creation & pattern detection</span>
        </div>
        <div className="panel-loading">Loading forge data...</div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Buddy Forge</h2>
          <span className="panel-subtitle">Self-improving skill creation & pattern detection</span>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', color: '#991b1b', padding: '12px 16px', borderRadius: 8, marginBottom: 16, fontSize: '0.9rem' }}>
          {error}
          <button
            onClick={loadData}
            style={{ marginLeft: 12, background: 'transparent', border: '1px solid #991b1b', color: '#991b1b', padding: '2px 10px', borderRadius: 4, cursor: 'pointer', fontSize: '0.8rem' }}
          >
            Retry
          </button>
        </div>
      )}

      <Snackbar message={snackbar} />

      {/* Stats Grid */}
      {stats && (
        <div className="forge-stats-grid">
          <div className="forge-stat-card">
            <div className="forge-stat-value">{stats.total_skills}</div>
            <div className="forge-stat-label">Total Skills</div>
          </div>
          <div className="forge-stat-card">
            <div className="forge-stat-value">{stats.total_patterns}</div>
            <div className="forge-stat-label">Patterns</div>
          </div>
          <div className="forge-stat-card">
            <div className="forge-stat-value">{stats.patterns_ready_for_promotion}</div>
            <div className="forge-stat-label">Promotable</div>
          </div>
          <div className="forge-stat-card">
            <div className="forge-stat-value" style={{ color: percentColor(stats.avg_success_rate) }}>
              {(stats.avg_success_rate * 100).toFixed(1)}%
            </div>
            <div className="forge-stat-label">Avg Success Rate</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="forge-tabs">
        <button
          className={`forge-tab ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          Skills ({skills.length})
        </button>
        <button
          className={`forge-tab ${activeTab === 'patterns' ? 'active' : ''}`}
          onClick={() => setActiveTab('patterns')}
        >
          Patterns ({patterns.patterns.length})
        </button>
        <button
          className={`forge-tab ${activeTab === 'create' ? 'active' : ''}`}
          onClick={() => setActiveTab('create')}
        >
          Create
        </button>
      </div>

      {/* Tab Content */}
      <div style={{ marginTop: 20 }}>
        {/* Skills Tab */}
        {activeTab === 'skills' && (
          skills.length === 0 ? (
            <div className="panel-empty">No forged skills yet. Observe interactions or create one manually.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {skills.map((skill) => (
                <div
                  key={skill.skill_id}
                  className="forge-skill-card"
                  onClick={() => setSelectedSkill(skill)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="forge-skill-header">
                    <span className="forge-skill-name">{skill.name}</span>
                    <span className={`forge-skill-status ${statusClass(skill.status)}`}>
                      {skill.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 8, marginTop: 4 }}>
                    {skill.description}
                  </div>
                  <div className="forge-skill-meta">
                    <span>{skill.category}</span>
                    <span>v{skill.versions.length > 0 ? skill.versions[skill.versions.length - 1].version : '0'}</span>
                    <span>{skill.total_executions} execs</span>
                    <span style={{ color: percentColor(skill.latest_success_rate) }}>
                      {(skill.latest_success_rate * 100).toFixed(0)}% success
                    </span>
                    {skill.versions.length > 0 && (
                      <span>~{(skill.versions[skill.versions.length - 1].avg_latency_ms / 1000).toFixed(1)}s</span>
                    )}
                  </div>
                  {skill.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
                      {skill.tags.map((tag) => (
                        <span key={tag} style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem', color: '#374151' }}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                    {skill.status === 'active' && (
                      <>
                        <button
                          className="btn-secondary"
                          style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            const latest = skill.versions[skill.versions.length - 1];
                            openEvolveModal(skill.skill_id, latest?.prompt_template || '');
                          }}
                        >
                          Evolve
                        </button>
                        <button
                          className="btn-secondary"
                          style={{ fontSize: '0.75rem', padding: '4px 10px', color: '#ef4444' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeprecate(skill.skill_id);
                          }}
                        >
                          Deprecate
                        </button>
                      </>
                    )}
                    {skill.status === 'deprecated' && (
                      <button
                        className="btn-secondary"
                        style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleArchive(skill.skill_id);
                        }}
                      >
                        Archive
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {/* Patterns Tab */}
        {activeTab === 'patterns' && (
          patterns.patterns.length === 0 ? (
            <div className="panel-empty">No interaction patterns detected yet. Keep interacting to let the forge learn.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {patterns.patterns.map((pattern) => (
                <div key={pattern.pattern_id} className="forge-pattern-card">
                  <div className="forge-pattern-header">
                    <span className="forge-pattern-name">
                      {pattern.suggested_category
                        ? `${pattern.suggested_category} pattern`
                        : `Pattern ${pattern.pattern_id.slice(0, 8)}`}
                    </span>
                    {patterns.promotable.some((p) => p.pattern_id === pattern.pattern_id) && (
                      <span style={{ fontSize: '0.7rem', background: '#dbeafe', color: '#1d4ed8', padding: '2px 8px', borderRadius: 4, fontWeight: 600 }}>
                        READY
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#374151', marginBottom: 8 }}>
                    {pattern.description}
                  </div>
                  {pattern.trigger_phrases.length > 0 && (
                    <div style={{ marginBottom: 4 }}>
                      <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>Triggers: </span>
                      {pattern.trigger_phrases.slice(0, 3).map((phrase, idx) => (
                        <span key={idx} style={{ fontSize: '0.75rem', background: '#f3f4f6', padding: '1px 6px', borderRadius: 3, marginRight: 4 }}>
                          {phrase.length > 40 ? phrase.slice(0, 40) + '...' : phrase}
                        </span>
                      ))}
                      {pattern.trigger_phrases.length > 3 && (
                        <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>+{pattern.trigger_phrases.length - 3} more</span>
                      )}
                    </div>
                  )}
                  <div className="forge-pattern-confidence" style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>Confidence: </span>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 120, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden', display: 'inline-block' }}>
                        <div style={{ width: `${(pattern.confidence * 100).toFixed(0)}%`, height: '100%', background: percentColor(pattern.confidence), borderRadius: 3 }} />
                      </div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: percentColor(pattern.confidence) }}>
                        {(pattern.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="forge-pattern-frequency">
                    <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>Frequency: {pattern.frequency}x</span>
                    <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                      Last seen: {formatDate(pattern.last_seen)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    {patterns.promotable.some((p) => p.pattern_id === pattern.pattern_id) && (
                      <button
                        className="btn-primary"
                        style={{ fontSize: '0.75rem', padding: '4px 12px' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          openPromoteModal(pattern);
                        }}
                      >
                        Promote to Skill
                      </button>
                    )}
                    {pattern.action_sequence.length > 0 && (
                      <div style={{ flex: 1, fontSize: '0.7rem', color: '#9ca3af', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', lineHeight: '26px' }}>
                        {pattern.action_sequence.slice(0, 3).join(' → ')}
                        {pattern.action_sequence.length > 3 ? '...' : ''}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {/* Create Tab */}
        {activeTab === 'create' && (
          <div style={{ maxWidth: 600 }}>
            <div className="forge-create-form">
              <div style={{ textAlign: 'center', marginBottom: 20 }}>
                <button
                  className="btn-primary"
                  onClick={() => {
                    setShowCreateForm(true);
                    setCreateName('');
                    setCreateDescription('');
                    setCreateCategory('utility');
                    setCreatePrompt('');
                    setCreateTags('');
                  }}
                >
                  + Create New Skill
                </button>
              </div>
              <div className="panel-empty">
                Use the button above to create a new skill, or go to the <strong>Patterns</strong> tab to promote detected patterns.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Selected Skill Detail Modal */}
      {selectedSkill && (
        <div className="forge-modal" onClick={() => setSelectedSkill(null)}>
          <div
            style={{
              background: '#fff',
              borderRadius: 12,
              padding: 24,
              width: 640,
              maxWidth: '90vw',
              maxHeight: '80vh',
              overflowY: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="forge-skill-header" style={{ marginBottom: 8 }}>
              <span className="forge-skill-name" style={{ fontSize: '1.1rem' }}>{selectedSkill.name}</span>
              <span className={`forge-skill-status ${statusClass(selectedSkill.status)}`}>
                {selectedSkill.status}
              </span>
            </div>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 16 }}>
              {selectedSkill.description}
            </div>
            <div style={{ marginBottom: 16 }}>
              <table style={{ width: '100%', fontSize: '0.8rem' }}>
                <tbody>
                  <tr>
                    <td style={{ padding: '6px 0', color: '#9ca3af', width: 120 }}>Category</td>
                    <td style={{ fontWeight: 600 }}>{selectedSkill.category}</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '6px 0', color: '#9ca3af' }}>Total Executions</td>
                    <td style={{ fontWeight: 600 }}>{selectedSkill.total_executions}</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '6px 0', color: '#9ca3af' }}>Latest Success</td>
                    <td style={{ fontWeight: 600, color: percentColor(selectedSkill.latest_success_rate) }}>
                      {(selectedSkill.latest_success_rate * 100).toFixed(1)}%
                    </td>
                  </tr>
                  <tr>
                    <td style={{ padding: '6px 0', color: '#9ca3af' }}>Rating</td>
                    <td style={{ fontWeight: 600 }}>{selectedSkill.average_rating?.toFixed(1) || 'N/A'}</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '6px 0', color: '#9ca3af' }}>Created</td>
                    <td style={{ fontWeight: 600 }}>{formatDate(selectedSkill.created_at)}</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '6px 0', color: '#9ca3af' }}>Updated</td>
                    <td style={{ fontWeight: 600 }}>{formatDate(selectedSkill.updated_at)}</td>
                  </tr>
                  {selectedSkill.tags.length > 0 && (
                    <tr>
                      <td style={{ padding: '6px 0', color: '#9ca3af' }}>Tags</td>
                      <td>
                        {selectedSkill.tags.map((t) => (
                          <span key={t} style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem', marginRight: 4 }}>
                            {t}
                          </span>
                        ))}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Version History */}
            {selectedSkill.versions.length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 12 }}>Version History</h4>
                <div className="forge-skill-versions">
                  {selectedSkill.versions.map((v) => (
                    <div
                      key={v.version}
                      style={{
                        padding: 12,
                        background: '#f9fafb',
                        borderRadius: 8,
                        marginBottom: 8,
                        border: '1px solid #e5e7eb',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>v{v.version}</span>
                        <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{formatDate(v.created_at)}</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: 6 }}>
                        <strong>Prompt:</strong>{' '}
                        {v.prompt_template.length > 120
                          ? v.prompt_template.slice(0, 120) + '...'
                          : v.prompt_template}
                      </div>
                      <div style={{ display: 'flex', gap: 16, fontSize: '0.7rem' }}>
                        <span style={{ color: percentColor(v.success_rate) }}>
                          {(v.success_rate * 100).toFixed(0)}% ({v.execution_count} execs)
                        </span>
                        <span>~{v.avg_tokens} tokens</span>
                        <span>{(v.avg_latency_ms / 1000).toFixed(2)}s</span>
                      </div>
                      {v.parameters.length > 0 && (
                        <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {v.parameters.map((p) => (
                            <span key={p.name} style={{ fontSize: '0.65rem', background: p.required ? '#fef3c7' : '#f3f4f6', padding: '1px 6px', borderRadius: 3 }}>
                              {p.name}: {p.type}{p.required ? '*' : ''}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
              {selectedSkill.status === 'active' && (
                <>
                  <button
                    className="btn-primary"
                    onClick={() => {
                      const latest = selectedSkill.versions[selectedSkill.versions.length - 1];
                      openEvolveModal(selectedSkill.skill_id, latest?.prompt_template || '');
                      setSelectedSkill(null);
                    }}
                  >
                    Evolve
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => {
                      handleDeprecate(selectedSkill.skill_id);
                      setSelectedSkill(null);
                    }}
                  >
                    Deprecate
                  </button>
                </>
              )}
              {selectedSkill.status === 'deprecated' && (
                <button
                  className="btn-secondary"
                  onClick={() => {
                    handleArchive(selectedSkill.skill_id);
                    setSelectedSkill(null);
                  }}
                >
                  Archive
                </button>
              )}
              <button
                className="btn-secondary"
                onClick={() => setSelectedSkill(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Skill Form Modal */}
      {showCreateForm && (
        <div className="forge-modal" onClick={() => setShowCreateForm(false)}>
          <div
            className="forge-create-form"
            style={{
              background: '#fff',
              borderRadius: 12,
              padding: 24,
              width: 520,
              maxWidth: '90vw',
              maxHeight: '80vh',
              overflowY: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 16 }}>Create Forged Skill</h3>

            <div className="forge-form-group">
              <label>Name</label>
              <input
                type="text"
                placeholder="e.g. summarize-transcript"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
              />
            </div>

            <div className="forge-form-group">
              <label>Description</label>
              <textarea
                placeholder="What does this skill do?"
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                rows={2}
              />
            </div>

            <div className="forge-form-group">
              <label>Category</label>
              <select value={createCategory} onChange={(e) => setCreateCategory(e.target.value)}>
                {CATEGORY_OPTIONS.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            <div className="forge-form-group">
              <label>Prompt Template</label>
              <textarea
                placeholder="The instruction/prompt template for this skill..."
                value={createPrompt}
                onChange={(e) => setCreatePrompt(e.target.value)}
                rows={4}
              />
            </div>

            <div className="forge-form-group">
              <label>Tags (comma separated)</label>
              <input
                type="text"
                placeholder="e.g. nlp, text, summary"
                value={createTags}
                onChange={(e) => setCreateTags(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn-secondary" onClick={() => setShowCreateForm(false)}>Cancel</button>
              <button
                className="btn-primary"
                onClick={handleCreate}
                disabled={createLoading || !createName.trim() || !createDescription.trim()}
              >
                {createLoading ? 'Creating...' : 'Create Skill'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Evolve Skill Modal */}
      {evolveSkillId && (
        <div className="forge-modal" onClick={() => setEvolveSkillId(null)}>
          <div
            style={{
              background: '#fff',
              borderRadius: 12,
              padding: 24,
              width: 520,
              maxWidth: '90vw',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 16 }}>Evolve Skill</h3>

            <div className="forge-form-group">
              <label>New Prompt Template</label>
              <textarea
                placeholder="Updated prompt template..."
                value={evolvePrompt}
                onChange={(e) => setEvolvePrompt(e.target.value)}
                rows={5}
              />
            </div>

            <div className="forge-form-group">
              <label>Reason for evolution (optional)</label>
              <input
                type="text"
                placeholder="Why are you evolving this skill?"
                value={evolveReason}
                onChange={(e) => setEvolveReason(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn-secondary" onClick={() => setEvolveSkillId(null)}>Cancel</button>
              <button
                className="btn-primary"
                onClick={() => handleEvolve(evolveSkillId)}
                disabled={evolveLoading || !evolvePrompt.trim()}
              >
                {evolveLoading ? 'Evolving...' : 'Evolve'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Promote Pattern Modal */}
      {promotePattern && (
        <div className="forge-modal" onClick={() => setPromotePattern(null)}>
          <div
            style={{
              background: '#fff',
              borderRadius: 12,
              padding: 24,
              width: 520,
              maxWidth: '90vw',
              maxHeight: '80vh',
              overflowY: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 16 }}>Promote Pattern to Skill</h3>

            <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: 12 }}>
              Promoting pattern: <strong>{promotePattern.description.slice(0, 100)}</strong>
            </div>

            <div className="forge-form-group">
              <label>Skill Name</label>
              <input
                type="text"
                value={promoteName}
                onChange={(e) => setPromoteName(e.target.value)}
              />
            </div>

            <div className="forge-form-group">
              <label>Description</label>
              <textarea
                value={promoteDescription}
                onChange={(e) => setPromoteDescription(e.target.value)}
                rows={2}
              />
            </div>

            <div className="forge-form-group">
              <label>Prompt Template</label>
              <textarea
                value={promotePrompt}
                onChange={(e) => setPromotePrompt(e.target.value)}
                rows={4}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn-secondary" onClick={() => setPromotePattern(null)}>Cancel</button>
              <button
                className="btn-primary"
                onClick={() => handlePromote(promotePattern)}
                disabled={promoteLoading || !promoteName.trim() || !promoteDescription.trim() || !promotePrompt.trim()}
              >
                {promoteLoading ? 'Promoting...' : 'Promote'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Styles */}
      <style>{`
        .forge-stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 12px;
          margin-bottom: 24px;
        }
        .forge-stat-card {
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          padding: 16px;
          text-align: center;
        }
        .forge-stat-value {
          font-size: 1.6rem;
          font-weight: 700;
          color: #111827;
        }
        .forge-stat-label {
          font-size: 0.75rem;
          color: #9ca3af;
          margin-top: 4px;
        }

        .forge-tabs {
          display: flex;
          gap: 0;
          border-bottom: 2px solid #e5e7eb;
        }
        .forge-tab {
          padding: 10px 20px;
          background: transparent;
          border: none;
          border-bottom: 2px solid transparent;
          margin-bottom: -2px;
          font-size: 0.85rem;
          font-weight: 600;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.15s;
        }
        .forge-tab:hover {
          color: #374151;
        }
        .forge-tab.active {
          color: #3b82f6;
          border-bottom-color: #3b82f6;
        }

        .forge-skill-card {
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          padding: 16px;
          transition: border-color 0.15s;
        }
        .forge-skill-card:hover {
          border-color: #3b82f6;
        }
        .forge-skill-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .forge-skill-name {
          font-weight: 600;
          font-size: 0.95rem;
          color: #111827;
        }
        .forge-skill-status {
          font-size: 0.7rem;
          font-weight: 600;
          padding: 2px 10px;
          border-radius: 10px;
          text-transform: uppercase;
        }
        .forge-skill-status.active {
          background: #d1fae5;
          color: #065f46;
        }
        .forge-skill-status.deprecated {
          background: #fef3c7;
          color: #92400e;
        }
        .forge-skill-status.archived {
          background: #f3f4f6;
          color: #6b7280;
        }
        .forge-skill-meta {
          display: flex;
          gap: 16px;
          font-size: 0.75rem;
          color: #9ca3af;
          flex-wrap: wrap;
        }

        .forge-skill-versions {
          max-height: 240px;
          overflow-y: auto;
        }

        .forge-pattern-card {
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          padding: 16px;
          transition: border-color 0.15s;
        }
        .forge-pattern-card:hover {
          border-color: #8b5cf6;
        }
        .forge-pattern-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 4px;
        }
        .forge-pattern-name {
          font-weight: 600;
          font-size: 0.9rem;
          color: #111827;
        }
        .forge-pattern-confidence {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .forge-pattern-frequency {
          display: flex;
          gap: 16px;
        }

        .forge-create-form {
        }

        .forge-form-group {
          margin-bottom: 12px;
        }
        .forge-form-group label {
          display: block;
          font-size: 0.85rem;
          font-weight: 600;
          margin-bottom: 4px;
          color: #374151;
        }
        .forge-form-group input,
        .forge-form-group textarea,
        .forge-form-group select {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 0.9rem;
          font-family: inherit;
          box-sizing: border-box;
        }
        .forge-form-group textarea {
          resize: vertical;
        }
        .forge-form-group input:focus,
        .forge-form-group textarea:focus,
        .forge-form-group select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }

        .forge-modal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 100;
        }

        .panel-loading {
          text-align: center;
          padding: 60px;
          color: #9ca3af;
          font-size: 0.95rem;
        }
        .panel-empty {
          text-align: center;
          padding: 40px;
          color: #9ca3af;
          font-size: 0.9rem;
        }

        .btn-primary {
          padding: 8px 20px;
          background: #3b82f6;
          color: #fff;
          border: none;
          border-radius: 6px;
          font-weight: 600;
          cursor: pointer;
          font-size: 0.85rem;
          font-family: inherit;
        }
        .btn-primary:hover {
          background: #2563eb;
        }
        .btn-primary:disabled {
          background: #93c5fd;
          cursor: not-allowed;
        }

        .btn-secondary {
          padding: 8px 20px;
          background: #f3f4f6;
          color: #374151;
          border: none;
          border-radius: 6px;
          font-weight: 600;
          cursor: pointer;
          font-size: 0.85rem;
          font-family: inherit;
        }
        .btn-secondary:hover {
          background: #e5e7eb;
        }
        .btn-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

const Snackbar: React.FC<{ message: { message: string; type: 'success' | 'error' } | null }> = ({ message }) => {
  if (!message) return null;
  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        padding: '12px 20px',
        borderRadius: 8,
        fontSize: '0.85rem',
        fontWeight: 600,
        color: '#fff',
        background: message.type === 'success' ? '#10b981' : '#ef4444',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        zIndex: 200,
        animation: 'forge-fadein 0.2s ease',
      }}
    >
      {message.message}
    </div>
  );
};