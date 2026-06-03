import React, { useState, useEffect } from 'react';
import type { Agent, Skill } from '../types';
import { api } from '../api/client';

interface SkillPanelProps {
  agent: Agent;
}

const CATEGORY_ICONS: Record<string, string> = {
  text: '📝',
  analysis: '📊',
  creative: '💡',
  engineering: '⚙️',
  education: '📚',
};

const CATEGORY_LABELS: Record<string, string> = {
  text: 'Text Processing',
  analysis: 'Analysis',
  creative: 'Creative',
  engineering: 'Engineering',
  education: 'Education',
};

export const SkillPanel: React.FC<SkillPanelProps> = ({ agent }) => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [skillsData, catsData] = await Promise.all([
          api.skills.list(),
          api.skills.categories(),
        ]);
        setSkills(skillsData);
        setCategories(catsData);
      } catch (err) {
        console.error('Failed to load skills:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredSkills = selectedCategory
    ? skills.filter((s) => s.category === selectedCategory)
    : skills;

  const handleSelectSkill = (skill: Skill) => {
    setSelectedSkill(skill);
    const initialParams: Record<string, string> = {};
    Object.keys(skill.parameters).forEach((key) => {
      initialParams[key] = '';
    });
    setParams(initialParams);
    setResult(null);
  };

  const handleExecute = async () => {
    if (!selectedSkill) return;
    setExecuting(true);
    setResult(null);
    try {
      const res = await api.skills.execute(selectedSkill.name, agent.id, params);
      setResult(res.result);
    } catch (err) {
      setResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="skill-panel">
        <div className="skill-loading">Loading skills...</div>
      </div>
    );
  }

  return (
    <div className="skill-panel">
      <div className="skill-header">
        <h2>Skills for {agent.name}</h2>
        <span className="skill-count">{skills.length} skills available</span>
      </div>

      <div className="skill-categories">
        <button
          className={`skill-cat-btn ${!selectedCategory ? 'active' : ''}`}
          onClick={() => setSelectedCategory(null)}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            className={`skill-cat-btn ${selectedCategory === cat ? 'active' : ''}`}
            onClick={() => setSelectedCategory(cat)}
          >
            {CATEGORY_ICONS[cat] || '🔧'} {CATEGORY_LABELS[cat] || cat}
          </button>
        ))}
      </div>

      <div className="skill-content">
        <div className="skill-list">
          {filteredSkills.map((skill) => (
            <div
              key={skill.name}
              className={`skill-card ${selectedSkill?.name === skill.name ? 'active' : ''}`}
              onClick={() => handleSelectSkill(skill)}
            >
              <div className="skill-card-icon">
                {CATEGORY_ICONS[skill.category] || '🔧'}
              </div>
              <div className="skill-card-info">
                <div className="skill-card-name">{skill.name}</div>
                <div className="skill-card-desc">{skill.description}</div>
                <div className="skill-card-cat">{CATEGORY_LABELS[skill.category] || skill.category}</div>
              </div>
            </div>
          ))}
          {filteredSkills.length === 0 && (
            <div className="skill-empty">No skills in this category.</div>
          )}
        </div>

        {selectedSkill && (
          <div className="skill-execute">
            <h3>{selectedSkill.name}</h3>
            <p className="skill-execute-desc">{selectedSkill.description}</p>

            {Object.entries(selectedSkill.parameters).map(([key, desc]) => (
              <div className="form-group" key={key}>
                <label>{key} <span className="param-hint">{desc}</span></label>
                {key === 'text' || key === 'code' || key === 'concept' || key === 'options' ? (
                  <textarea
                    placeholder={`Enter ${key}...`}
                    value={params[key] || ''}
                    onChange={(e) => setParams({ ...params, [key]: e.target.value })}
                    rows={key === 'code' ? 6 : 3}
                  />
                ) : (
                  <input
                    type="text"
                    placeholder={`Enter ${key}...`}
                    value={params[key] || ''}
                    onChange={(e) => setParams({ ...params, [key]: e.target.value })}
                  />
                )}
              </div>
            ))}

            <button
              className="btn-primary btn-full"
              onClick={handleExecute}
              disabled={executing}
            >
              {executing ? 'Executing...' : 'Execute Skill'}
            </button>

            {result && (
              <div className="skill-result">
                <div className="skill-result-header">Result</div>
                <div className="skill-result-content">{result}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};