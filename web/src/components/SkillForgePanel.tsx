import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#0d9488',
  secondary: '#5eead4',
  bg: '#f0fdfa',
  border: '#99f6e4',
  accent: '#ccfbf1',
  text: '#134e4a',
};

export const SkillForgePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'test' | 'evolve'>('overview');

  // Create skill form
  const [createForm, setCreateForm] = useState({
    name: '', description: '', trigger_conditions: '', procedure: '',
  });

  // Test form
  const [testForm, setTestForm] = useState({
    skill_id: '', test_prompt: '', expected_behavior: '',
  });

  // Evolve form
  const [evolveForm, setEvolveForm] = useState({
    skill_id: '', change_description: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.skillForge.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load skill forge data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateSkill = async () => {
    if (!createForm.name.trim() || !createForm.description.trim()) return;
    try {
      await api.skillForge.createSkill({
        name: createForm.name.trim(),
        description: createForm.description.trim(),
        trigger_conditions: createForm.trigger_conditions.split(',').map(s => s.trim()).filter(Boolean),
        procedure: createForm.procedure.split(',').map(s => s.trim()).filter(Boolean),
      });
      toast.success(`Skill "${createForm.name}" created`);
      setCreateForm({ name: '', description: '', trigger_conditions: '', procedure: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDesignTest = async () => {
    if (!testForm.skill_id.trim() || !testForm.test_prompt.trim() || !testForm.expected_behavior.trim()) return;
    try {
      await api.skillForge.designTest({
        skill_id: testForm.skill_id.trim(),
        test_prompt: testForm.test_prompt.trim(),
        expected_behavior: testForm.expected_behavior.trim(),
      });
      toast.success('Test designed for skill');
      setTestForm({ skill_id: '', test_prompt: '', expected_behavior: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleEvolve = async () => {
    if (!evolveForm.skill_id.trim() || !evolveForm.change_description.trim()) return;
    try {
      await api.skillForge.evolve({
        skill_id: evolveForm.skill_id.trim(),
        change_description: evolveForm.change_description.trim(),
      });
      toast.success('Skill evolution submitted');
      setEvolveForm({ skill_id: '', change_description: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>⚒️ Skill Forge</h2>
          <p className="panel-subtitle">Craft, test, and evolve agent skills</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading skill forge...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>⚒️ Skill Forge</h2>
        <p className="panel-subtitle">Craft, test, and evolve agent skills</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_skills ?? '-'}</span><span className="stat-label">Total Skills</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.active_skills ?? '-'}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_tests ?? '-'}</span><span className="stat-label">Tests</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_evolutions ?? '-'}</span><span className="stat-label">Evolutions</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'test', 'evolve'] as const).map(s => (
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
            <h3 style={{ color: themeColors.text }}>Skill Forge Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Skills</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_skills ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Skills</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.active_skills ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Tests Designed</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_tests ?? 0}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Evolutions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_evolutions ?? 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Skill */}
      {activeSection === 'create' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Skill</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={createForm.name}
                onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Skill name..."
              />
            </div>
            <div className="form-group">
              <label>Description *</label>
              <textarea
                rows={3}
                value={createForm.description}
                onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this skill does..."
              />
            </div>
            <div className="form-group">
              <label>Trigger Conditions (comma-separated)</label>
              <input
                type="text"
                value={createForm.trigger_conditions}
                onChange={e => setCreateForm(f => ({ ...f, trigger_conditions: e.target.value }))}
                placeholder="user asks for code review, error detected"
              />
            </div>
            <div className="form-group">
              <label>Procedure (comma-separated)</label>
              <input
                type="text"
                value={createForm.procedure}
                onChange={e => setCreateForm(f => ({ ...f, procedure: e.target.value }))}
                placeholder="analyze input, generate plan, execute, verify"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateSkill}
              disabled={!createForm.name.trim() || !createForm.description.trim()}
            >
              ⚒️ Create Skill
            </button>
          </div>
        </div>
      )}

      {/* Test */}
      {activeSection === 'test' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Design Test</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Skill ID *</label>
              <input
                type="text"
                value={testForm.skill_id}
                onChange={e => setTestForm(f => ({ ...f, skill_id: e.target.value }))}
                placeholder="Enter skill ID"
              />
            </div>
            <div className="form-group">
              <label>Test Prompt *</label>
              <textarea
                rows={3}
                value={testForm.test_prompt}
                onChange={e => setTestForm(f => ({ ...f, test_prompt: e.target.value }))}
                placeholder="Prompt to exercise the skill..."
              />
            </div>
            <div className="form-group">
              <label>Expected Behavior *</label>
              <textarea
                rows={3}
                value={testForm.expected_behavior}
                onChange={e => setTestForm(f => ({ ...f, expected_behavior: e.target.value }))}
                placeholder="Describe the expected outcome..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleDesignTest}
              disabled={!testForm.skill_id.trim() || !testForm.test_prompt.trim() || !testForm.expected_behavior.trim()}
            >
              Design Test
            </button>
          </div>
        </div>
      )}

      {/* Evolve */}
      {activeSection === 'evolve' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Evolve Skill</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Skill ID *</label>
              <input
                type="text"
                value={evolveForm.skill_id}
                onChange={e => setEvolveForm(f => ({ ...f, skill_id: e.target.value }))}
                placeholder="Enter skill ID to evolve"
              />
            </div>
            <div className="form-group">
              <label>Change Description *</label>
              <textarea
                rows={3}
                value={evolveForm.change_description}
                onChange={e => setEvolveForm(f => ({ ...f, change_description: e.target.value }))}
                placeholder="Describe how the skill should evolve..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleEvolve}
              disabled={!evolveForm.skill_id.trim() || !evolveForm.change_description.trim()}
            >
              Evolve Skill
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillForgePanel;
