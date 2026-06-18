import React, { useState, useEffect, useCallback } from 'react';
import type { Agent, AgentPersonaProfile, PersonaStats } from '../types';
import { api } from '../api/client';
import { useToast } from './Toast';

interface PersonaPanelProps {
  agent: Agent;
}

const TRAIT_LABELS: Record<string, string> = {
  analytical: 'Analytical',
  creative: 'Creative',
  precise: 'Precise',
  empathetic: 'Empathetic',
  decisive: 'Decisive',
  cautious: 'Cautious',
  enthusiastic: 'Enthusiastic',
  pragmatic: 'Pragmatic',
  visionary: 'Visionary',
  detailed: 'Detailed',
  concise: 'Concise',
  playful: 'Playful',
};

const STYLE_LABELS: Record<string, string> = {
  assistant: 'Assistant',
  mentor: 'Mentor',
  collaborator: 'Collaborator',
  coach: 'Coach',
  analyst: 'Analyst',
  storyteller: 'Storyteller',
  executor: 'Executor',
};

const DECISION_LABELS: Record<string, string> = {
  systematic: 'Systematic',
  intuitive: 'Intuitive',
  analytical: 'Analytical',
  collaborative: 'Collaborative',
  autonomous: 'Autonomous',
  cautious: 'Cautious',
};

export const PersonaPanel: React.FC<PersonaPanelProps> = ({ agent }) => {
  const toast = useToast();
  const [personas, setPersonas] = useState<AgentPersonaProfile[]>([]);
  const [activePersona, setActivePersona] = useState<AgentPersonaProfile | null>(null);
  const [stats, setStats] = useState<PersonaStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    role: 'general_assistant',
    style: 'assistant',
    decision: 'systematic',
    traits: {} as Record<string, number>,
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [personaList, personaStats, active] = await Promise.all([
        api.agentPersona.list(),
        api.agentPersona.stats(),
        api.agentPersona.getActive().catch(() => null),
      ]);
      setPersonas(personaList.personas);
      setStats(personaStats);
      setActivePersona(active);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load personas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleActivate = async (personaId: string) => {
    try {
      const result = await api.agentPersona.activate(personaId);
      if (result.success && result.active) {
        setActivePersona(result.active);
        toast.success('Persona activated');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to activate persona');
    }
  };

  const handleCreateCustom = async () => {
    if (!createForm.name.trim()) return;
    try {
      const persona = await api.agentPersona.create({
        name: createForm.name,
        description: createForm.description,
        traits: createForm.traits,
        style: createForm.style,
        decision: createForm.decision,
        role: createForm.role,
      });
      setPersonas(prev => [...prev, persona]);
      setShowCreate(false);
      setCreateForm({
        name: '', description: '', role: 'general_assistant',
        style: 'assistant', decision: 'systematic', traits: {},
      });
      toast.success('Persona created');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create persona');
    }
  };

  const toggleTrait = (traitKey: string) => {
    setCreateForm(f => {
      const traits = { ...f.traits };
      if (traits[traitKey]) {
        delete traits[traitKey];
      } else {
        traits[traitKey] = 0.7;
      }
      return { ...f, traits };
    });
  };

  const getTraitColor = (value: number) => {
    if (value >= 0.8) return '#22c55e';
    if (value >= 0.6) return '#3b82f6';
    if (value >= 0.4) return '#f59e0b';
    return '#9ca3af';
  };

  if (loading) {
    return <div className="panel-container"><div className="panel-loading"><div className="spinner" /><span>Loading personas...</span></div></div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Persona Management</h2>
          <div className="panel-subtitle">{agent.name} — {personas.length} persona{personas.length !== 1 ? 's' : ''} available</div>
        </div>
        <div className="panel-header-actions">
          <button className="btn-sm" onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? 'Cancel' : '+ Custom Persona'}
          </button>
          <button className="btn-sm" onClick={loadData} style={{ marginLeft: '8px' }}>Refresh</button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-icon">Total</span>
            <div className="stat-content">
              <span className="stat-value">{stats.total_personas}</span>
              <span className="stat-label">Personas</span>
            </div>
          </div>
          <div className="stat-item">
            <span className="stat-icon">Active</span>
            <div className="stat-content">
              <span className="stat-value" style={{ fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {stats.active_persona || 'None'}
              </span>
              <span className="stat-label">Active Persona</span>
            </div>
          </div>
          {Object.entries(stats.roles || {}).slice(0, 3).map(([role, count]) => (
            <div className="stat-item" key={role}>
              <span className="stat-icon">{role.charAt(0).toUpperCase()}</span>
              <div className="stat-content">
                <span className="stat-value">{count as number}</span>
                <span className="stat-label">{role}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Custom Persona Form */}
      {showCreate && (
        <div className="skill-execute" style={{ marginBottom: '20px', position: 'static' }}>
          <h3>Create Custom Persona</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={createForm.name}
                onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Code Mentor"
              />
            </div>
            <div className="form-group">
              <label>Role</label>
              <select value={createForm.role} onChange={e => setCreateForm(f => ({ ...f, role: e.target.value }))}>
                <option value="general_assistant">General Assistant</option>
                <option value="code_mentor">Code Mentor</option>
                <option value="research_partner">Research Partner</option>
                <option value="creative_collaborator">Creative Collaborator</option>
                <option value="strategic_advisor">Strategic Advisor</option>
                <option value="data_analyst">Data Analyst</option>
                <option value="writing_assistant">Writing Assistant</option>
                <option value="devops_engineer">DevOps Engineer</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Description</label>
            <input
              type="text"
              value={createForm.description}
              onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
              placeholder="What this persona does..."
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Interaction Style</label>
              <select value={createForm.style} onChange={e => setCreateForm(f => ({ ...f, style: e.target.value }))}>
                {Object.entries(STYLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Decision Style</label>
              <select value={createForm.decision} onChange={e => setCreateForm(f => ({ ...f, decision: e.target.value }))}>
                {Object.entries(DECISION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Personality Traits</label>
            <div className="memory-tags" style={{ gap: '6px', marginTop: '4px' }}>
              {Object.entries(TRAIT_LABELS).map(([key, label]) => (
                <span
                  key={key}
                  className={`memory-card-tag ${createForm.traits[key] ? 'active' : ''}`}
                  onClick={() => toggleTrait(key)}
                  style={{
                    cursor: 'pointer',
                    background: createForm.traits[key] ? '#3b82f6' : 'var(--bg-card, #f3f4f6)',
                    color: createForm.traits[key] ? '#fff' : 'var(--text-secondary, #6b7280)',
                    border: createForm.traits[key] ? '1px solid #2563eb' : '1px solid var(--border, #d1d5db)',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    transition: 'all 0.15s',
                  }}
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
          <button className="btn-primary" onClick={handleCreateCustom} disabled={!createForm.name.trim()}>
            Create Persona
          </button>
        </div>
      )}

      {/* Active Persona */}
      {activePersona && (
        <div className="subagent-aggregated" style={{ marginBottom: '16px' }}>
          <div className="subagent-aggregated-header">ACTIVE PERSONA</div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text)', marginBottom: '4px' }}>
            {activePersona.name}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {STYLE_LABELS[activePersona.interaction_style] || activePersona.interaction_style} · {DECISION_LABELS[activePersona.decision_style] || activePersona.decision_style}
            {activePersona.description && ` — ${activePersona.description}`}
          </div>
          {activePersona.domain_expertise && activePersona.domain_expertise.length > 0 && (
            <div className="memory-tags" style={{ marginTop: '8px' }}>
              {activePersona.domain_expertise.map((area: string) => (
                <span key={area} className="memory-card-tag">{area}</span>
              ))}
            </div>
          )}
          {/* Trait bars */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
            {Object.entries(activePersona.traits || {}).slice(0, 8).map(([trait, value]) => (
              <div key={trait} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-secondary)', minWidth: '70px' }}>{TRAIT_LABELS[trait] || trait}</span>
                <div style={{ width: '60px', height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${(value as number) * 100}%`, height: '100%', background: getTraitColor(value as number), borderRadius: '3px' }} />
                </div>
                <span style={{ color: 'var(--text-muted)', minWidth: '28px' }}>{((value as number) * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Personas */}
      <div className="dashboard-section">
        <h3>All Personas</h3>
        {personas.length === 0 ? (
          <div className="panel-empty">No personas available. Create a custom persona above.</div>
        ) : (
          <div className="subagent-tasks">
            {personas.map(persona => (
              <div
                key={persona.persona_id}
                className={`skill-card ${activePersona?.persona_id === persona.persona_id ? 'active' : ''}`}
                style={{ cursor: 'default' }}
              >
                <div className="skill-card-icon" style={{
                  width: '12px', height: '12px', borderRadius: '50%',
                  background: activePersona?.persona_id === persona.persona_id ? '#22c55e' : '#9ca3af',
                  marginTop: '4px',
                }} />
                <div className="skill-card-info">
                  <div className="skill-card-name">
                    {persona.name}
                    {activePersona?.persona_id === persona.persona_id && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: '6px' }}>(active)</span>
                    )}
                  </div>
                  <div className="skill-card-desc">
                    {persona.description || `${STYLE_LABELS[persona.interaction_style] || persona.interaction_style} · ${DECISION_LABELS[persona.decision_style] || persona.decision_style}`}
                  </div>
                  <div className="skill-card-cat">
                    {persona.role.replace(/_/g, ' ')} · {persona.interaction_count} interactions
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {activePersona?.persona_id !== persona.persona_id && (
                    <button className="btn-sm" onClick={() => handleActivate(persona.persona_id)}>Activate</button>
                  )}
                  {activePersona?.persona_id === persona.persona_id && (
                    <span className="dashboard-badge active" style={{ padding: '4px 10px' }}>Active</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{styles}</style>
    </div>
  );
};

const styles = `
.panel-container { padding: 24px; max-width: 1400px; margin: 0 auto; }
.panel-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.panel-header h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; color: var(--text, #1f2937); }
.panel-subtitle { color: var(--text-secondary, #6b7280); font-size: 0.85rem; }
.panel-header-actions { display: flex; gap: 8px; }
.panel-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 0; color: var(--text-secondary); gap: 16px; }
.spinner { width: 32px; height: 32px; border: 3px solid var(--border); border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-banner { background: #fef2f2; color: #991b1b; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; }
.panel-empty { text-align: center; padding: 40px 0; color: var(--text-secondary); }
.stats-bar { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-item { flex: 1; min-width: 140px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 14px 18px; display: flex; align-items: center; gap: 12px; }
.stat-icon { font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; min-width: 40px; }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: 1.3rem; font-weight: 800; color: var(--text); }
.stat-label { font-size: 0.72rem; color: var(--text-secondary); font-weight: 600; }
.dashboard-section { margin-top: 24px; }
.dashboard-section h3 { font-size: 1rem; font-weight: 700; margin-bottom: 12px; color: var(--text); }
.subagent-tasks { display: flex; flex-direction: column; gap: 8px; }
.skill-card { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; transition: all 0.15s; }
.skill-card:hover { border-color: #3b82f6; }
.skill-card.active { border-color: #22c55e; background: #f0fdf4; }
.skill-card-icon { flex-shrink: 0; }
.skill-card-info { flex: 1; min-width: 0; }
.skill-card-name { font-size: 0.9rem; font-weight: 700; color: var(--text); }
.skill-card-desc { font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.skill-card-cat { font-size: 0.72rem; color: var(--text-muted); margin-top: 2px; text-transform: capitalize; }
.memory-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.memory-card-tag { padding: 2px 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; font-size: 0.7rem; color: var(--text-secondary); font-weight: 600; }
.subagent-aggregated { background: var(--bg-card); border: 1px solid #22c55e; border-radius: 12px; padding: 16px 20px; }
.subagent-aggregated-header { font-size: 0.7rem; font-weight: 800; color: #22c55e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.dashboard-badge { padding: 4px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; }
.dashboard-badge.active { background: #22c55e; color: #fff; }
.form-group { margin-bottom: 14px; flex: 1; }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; color: var(--text); }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.9rem; background: var(--bg-card); color: var(--text); font-family: inherit; }
.form-row { display: flex; gap: 12px; }
.btn-sm { padding: 6px 14px; background: var(--bg-card); color: var(--text); border: 1px solid var(--border); border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.btn-sm:hover { border-color: #3b82f6; color: #3b82f6; }
.btn-primary { padding: 10px 20px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; }
.btn-primary:hover { background: #2563eb; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.skill-execute { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.skill-execute h3 { font-size: 1.05rem; font-weight: 700; margin-bottom: 16px; color: var(--text); }
`;