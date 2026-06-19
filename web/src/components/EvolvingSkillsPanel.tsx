import React, { useState, useEffect } from 'react';

interface EvolvingSkill {
  skill_id: string;
  name: string;
  category: string;
  stage: string;
  total_executions: number;
  success_rate: number;
  variant_count: number;
}

interface SkillDetail {
  skill_id: string;
  name: string;
  category: string;
  stage: string;
  total_executions: number;
  success_rate: number;
  variant_count: number;
  best_variant_id: string | null;
  evolution_metrics: Record<string, any>;
  variants: {
    variant_id: string;
    strategy: string;
    success_rate: number;
    avg_quality: number;
    avg_latency: number;
    avg_tokens: number;
    execution_count: number;
    generation: number;
    is_active: boolean;
  }[];
  recent_executions: {
    execution_id: string;
    success: boolean;
    quality: number;
    latency_ms: number;
    tokens: number;
    timestamp: string;
  }[];
}

interface SkillsStats {
  total_skills: number;
  total_executions: number;
  total_evolutions: number;
  skills_by_stage: Record<string, number>;
  skills_by_category: Record<string, number>;
  top_skills: { skill_id: string; name: string; stage: string; success_rate: number; executions: number }[];
}

export const EvolvingSkillsPanel: React.FC = () => {
  const [stats, setStats] = useState<SkillsStats | null>(null);
  const [skills, setSkills] = useState<EvolvingSkill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({ name: '', category: 'general', description: '', prompt_template: '' });

  useEffect(() => {
    fetchStats();
    fetchSkills();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/evolving-skills/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch skills stats:', e); }
  };

  const fetchSkills = async () => {
    try {
      const res = await fetch('/api/evolving-skills/list');
      const data = await res.json();
      setSkills(data.skills || []);
    } catch (e) { console.error('Failed to fetch skills:', e); }
  };

  const fetchSkillDetail = async (skillId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/evolving-skills/${skillId}`);
      setSelectedSkill(await res.json());
    } catch (e) { console.error('Failed to fetch skill detail:', e); }
    setLoading(false);
  };

  const createSkill = async () => {
    try {
      await fetch('/api/evolving-skills/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      setShowCreate(false);
      setFormData({ name: '', category: 'general', description: '', prompt_template: '' });
      fetchStats();
      fetchSkills();
    } catch (e) { console.error('Failed to create skill:', e); }
  };

  const stageColor = (stage: string) => {
    const colors: Record<string, string> = {
      seed: '#94a3b8', sprouting: '#22c55e', growing: '#3b82f6',
      maturing: '#8b5cf6', refined: '#f59e0b', mastered: '#ef4444',
    };
    return colors[stage] || '#94a3b8';
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Self-Evolving Skills</h2>
        <span className="panel-subtitle">Skills that auto-improve through usage</span>
      </div>

      <div className="panel-content">
        {/* Stats */}
        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_skills}</div>
              <div className="stat-label">Skills</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_executions}</div>
              <div className="stat-label">Executions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_evolutions}</div>
              <div className="stat-label">Evolutions</div>
            </div>
          </div>
        )}

        {/* Stage Breakdown */}
        {stats?.skills_by_stage && (
          <div className="section">
            <h3>By Stage</h3>
            <div className="chip-row">
              {Object.entries(stats.skills_by_stage).map(([stage, count]) => (
                <span key={stage} className="chip" style={{ borderColor: stageColor(stage) }}>
                  {stage}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Create Button */}
        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : 'Create Skill'}
        </button>

        {showCreate && (
          <div className="form-card">
            <input className="text-input" placeholder="Name" value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })} />
            <input className="text-input" placeholder="Category" value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })} />
            <input className="text-input" placeholder="Description" value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })} />
            <textarea className="text-input" placeholder="Prompt Template" value={formData.prompt_template}
              onChange={e => setFormData({ ...formData, prompt_template: e.target.value })} rows={3} />
            <button className="btn btn-primary" onClick={createSkill}>Create</button>
          </div>
        )}

        {/* Skills List */}
        <div className="section">
          <h3>Skills ({skills.length})</h3>
          <div className="list">
            {skills.map(skill => (
              <div key={skill.skill_id} className="list-item" onClick={() => fetchSkillDetail(skill.skill_id)}>
                <div className="list-item-header">
                  <span className="list-item-name">{skill.name}</span>
                  <span className="badge" style={{ background: stageColor(skill.stage) }}>{skill.stage}</span>
                </div>
                <div className="list-item-meta">
                  <span>{skill.category}</span>
                  <span>Success: {(skill.success_rate * 100).toFixed(0)}%</span>
                  <span>{skill.total_executions} runs</span>
                  <span>{skill.variant_count} variants</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Skill Detail */}
        {selectedSkill && (
          <div className="section">
            <h3>Detail: {selectedSkill.name}</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{(selectedSkill.success_rate * 100).toFixed(1)}%</div>
                <div className="stat-label">Success Rate</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{selectedSkill.total_executions}</div>
                <div className="stat-label">Executions</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{selectedSkill.variant_count}</div>
                <div className="stat-label">Variants</div>
              </div>
            </div>

            <h4>Variants</h4>
            <div className="list">
              {selectedSkill.variants.map(v => (
                <div key={v.variant_id} className="list-item">
                  <div className="list-item-header">
                    <span className="badge">{v.strategy}</span>
                    <span>Gen {v.generation}</span>
                    <span className={v.is_active ? 'text-success' : 'text-muted'}>
                      {v.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="list-item-meta">
                    <span>Success: {(v.success_rate * 100).toFixed(0)}%</span>
                    <span>Quality: {(v.avg_quality * 100).toFixed(0)}%</span>
                    <span>Latency: {v.avg_latency.toFixed(0)}ms</span>
                    <span>Tokens: {v.avg_tokens.toFixed(0)}</span>
                    <span>{v.execution_count} runs</span>
                  </div>
                </div>
              ))}
            </div>

            <h4>Recent Executions</h4>
            <div className="list">
              {selectedSkill.recent_executions.map(e => (
                <div key={e.execution_id} className="list-item">
                  <span className={e.success ? 'text-success' : 'text-error'}>
                    {e.success ? '✓' : '✗'}
                  </span>
                  <span>Q: {(e.quality * 100).toFixed(0)}%</span>
                  <span>{e.latency_ms}ms</span>
                  <span>{e.tokens} tokens</span>
                  <span>{new Date(e.timestamp).toLocaleTimeString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};