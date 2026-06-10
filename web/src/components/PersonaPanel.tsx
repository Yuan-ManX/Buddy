import React, { useState, useEffect } from 'react';
import type { Agent, Persona } from '../types';
import { api } from '../api/client';

interface PersonaPanelProps {
  agent: Agent;
}

export const PersonaPanel: React.FC<PersonaPanelProps> = ({ agent }) => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [activePersona, setActivePersona] = useState<Persona | null>(null);
  const [presets, setPresets] = useState<Array<{ key: string; name: string; description: string; tone: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    tone: 'collaborator',
    verbosity: 'moderate',
    description: '',
    expertise_areas: '',
    communication_style: '',
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [personaList, presetsList] = await Promise.all([
        api.personas.list(agent.id),
        api.personas.presets(),
      ]);
      setPersonas(personaList);
      setPresets(presetsList);
      const active = personaList.find((p: Persona) => p.is_active);
      setActivePersona(active || personaList[0] || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load personas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [agent.id]);

  const handleActivate = async (personaId: string) => {
    try {
      await api.personas.activate(agent.id, personaId);
      const persona = personas.find(p => p.id === personaId);
      if (persona) setActivePersona(persona);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate persona');
    }
  };

  const handleCreatePreset = async (presetName: string) => {
    try {
      const persona = await api.personas.createFromPreset(agent.id, presetName);
      setPersonas(prev => [...prev, persona]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create persona');
    }
  };

  const handleCreateCustom = async () => {
    if (!createForm.name.trim()) return;
    try {
      const persona = await api.personas.create(agent.id, {
        name: createForm.name,
        tone: createForm.tone,
        verbosity: createForm.verbosity,
        description: createForm.description,
        expertise_areas: createForm.expertise_areas.split(',').map(s => s.trim()).filter(Boolean),
        communication_style: createForm.communication_style,
      });
      setPersonas(prev => [...prev, persona]);
      setShowCreate(false);
      setCreateForm({ name: '', tone: 'collaborator', verbosity: 'moderate', description: '', expertise_areas: '', communication_style: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create persona');
    }
  };

  const handleDelete = async (personaId: string) => {
    if (!confirm('Delete this persona?')) return;
    try {
      await api.personas.delete(agent.id, personaId);
      setPersonas(prev => prev.filter(p => p.id !== personaId));
      if (activePersona?.id === personaId) {
        const remaining = personas.filter(p => p.id !== personaId);
        setActivePersona(remaining.find(p => p.is_active) || remaining[0] || null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete persona');
    }
  };

  const toneColors: Record<string, string> = {
    professional: '#3b82f6',
    casual: '#8b5cf6',
    empathetic: '#ec4899',
    analytical: '#06b6d4',
    creative: '#f59e0b',
    direct: '#ef4444',
    mentor: '#10b981',
    collaborator: '#6366f1',
  };

  if (loading) {
    return <div className="panel-container"><div className="panel-loading">Loading personas...</div></div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Persona Management</h2>
          <div className="panel-subtitle">{agent.name} — {personas.length} persona{personas.length !== 1 ? 's' : ''}</div>
        </div>
        <div className="panel-header-actions">
          <button className="btn-sm" onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? 'Cancel' : '+ Custom Persona'}
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {showCreate && (
        <div className="skill-execute" style={{ marginBottom: '20px', position: 'static' }}>
          <h3>Create Custom Persona</h3>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              value={createForm.name}
              onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Code Mentor"
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Tone</label>
              <select value={createForm.tone} onChange={e => setCreateForm(f => ({ ...f, tone: e.target.value }))}>
                {Object.keys(toneColors).map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Verbosity</label>
              <select value={createForm.verbosity} onChange={e => setCreateForm(f => ({ ...f, verbosity: e.target.value }))}>
                <option value="minimal">Minimal</option>
                <option value="concise">Concise</option>
                <option value="moderate">Moderate</option>
                <option value="detailed">Detailed</option>
                <option value="comprehensive">Comprehensive</option>
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
          <div className="form-group">
            <label>Expertise Areas (comma-separated)</label>
            <input
              type="text"
              value={createForm.expertise_areas}
              onChange={e => setCreateForm(f => ({ ...f, expertise_areas: e.target.value }))}
              placeholder="coding, architecture, review"
            />
          </div>
          <div className="form-group">
            <label>Communication Style</label>
            <input
              type="text"
              value={createForm.communication_style}
              onChange={e => setCreateForm(f => ({ ...f, communication_style: e.target.value }))}
              placeholder="Technical and precise..."
            />
          </div>
          <button className="btn-primary" onClick={handleCreateCustom}>Create Persona</button>
        </div>
      )}

      {/* Active Persona */}
      {activePersona && (
        <div className="subagent-aggregated" style={{ marginBottom: '16px' }}>
          <div className="subagent-aggregated-header">ACTIVE PERSONA</div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text)', marginBottom: '4px' }}>
            <span style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: toneColors[activePersona.tone] || '#666',
              marginRight: '8px',
            }} />
            {activePersona.name}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {activePersona.tone} · {activePersona.verbosity}
            {activePersona.description && ` — ${activePersona.description}`}
          </div>
          {activePersona.expertise_areas && activePersona.expertise_areas.length > 0 && (
            <div className="memory-tags" style={{ marginTop: '8px' }}>
              {activePersona.expertise_areas.map((area: string) => (
                <span key={area} className="memory-card-tag">{area}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Preset Personas */}
      <div className="dashboard-section">
        <h3>Preset Personas</h3>
        <div className="subagent-tasks">
          {presets.map(preset => (
            <div key={preset.key} className="skill-card" style={{ cursor: 'default' }}>
              <div className="skill-card-icon" style={{
                width: '12px', height: '12px', borderRadius: '50%',
                background: toneColors[preset.tone] || '#666',
                marginTop: '4px',
              }} />
              <div className="skill-card-info">
                <div className="skill-card-name">{preset.name}</div>
                <div className="skill-card-desc">{preset.description}</div>
                <div className="skill-card-cat">{preset.tone}</div>
              </div>
              <button
                className="btn-sm"
                onClick={() => handleCreatePreset(preset.key)}
                disabled={personas.some(p => p.name === preset.name)}
              >
                {personas.some(p => p.name === preset.name) ? 'Added' : 'Add'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Custom Personas */}
      <div className="dashboard-section">
        <h3>Your Personas</h3>
        {personas.length === 0 ? (
          <div className="panel-empty">No personas created yet. Add a preset above or create a custom one.</div>
        ) : (
          <div className="subagent-tasks">
            {personas.map(persona => (
              <div
                key={persona.id}
                className={`skill-card ${activePersona?.id === persona.id ? 'active' : ''}`}
                style={{ cursor: 'default' }}
              >
                <div className="skill-card-icon" style={{
                  width: '12px', height: '12px', borderRadius: '50%',
                  background: toneColors[persona.tone] || '#666',
                  marginTop: '4px',
                }} />
                <div className="skill-card-info">
                  <div className="skill-card-name">
                    {persona.name}
                    {persona.is_active && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: '6px' }}>(default)</span>
                    )}
                  </div>
                  <div className="skill-card-desc">{persona.description || `${persona.tone} · ${persona.verbosity}`}</div>
                  <div className="skill-card-cat">{persona.tone} · {persona.verbosity}</div>
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {activePersona?.id !== persona.id && (
                    <button className="btn-sm" onClick={() => handleActivate(persona.id)}>Activate</button>
                  )}
                  {activePersona?.id === persona.id && (
                    <span className="dashboard-badge active" style={{ padding: '4px 10px' }}>Active</span>
                  )}
                  {!persona.is_active && (
                    <button className="btn-sm btn-danger" onClick={() => handleDelete(persona.id)}>×</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};