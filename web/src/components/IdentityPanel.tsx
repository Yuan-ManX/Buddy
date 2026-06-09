import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { IdentityProfile, Agent } from '../types';

interface Props {
  agent: Agent;
}

export const IdentityPanel: React.FC<Props> = ({ agent }) => {
  const [profile, setProfile] = useState<IdentityProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'attributes' | 'personas' | 'learning'>('attributes');
  const [newAttrKey, setNewAttrKey] = useState('');
  const [newAttrValue, setNewAttrValue] = useState('');
  const [newAttrCategory, setNewAttrCategory] = useState('preference');
  const [newPersonaName, setNewPersonaName] = useState('');
  const [newPersonaType, setNewPersonaType] = useState('companion');
  const [newPersonaDesc, setNewPersonaDesc] = useState('');
  const [newPersonaTone, setNewPersonaTone] = useState('professional');
  const [newPersonaVerbosity, setNewPersonaVerbosity] = useState('moderate');
  const [newPersonaExpertise, setNewPersonaExpertise] = useState('');
  const toast = useToast();

  const loadProfile = async () => {
    try {
      setLoading(true);
      const p = await api.identity.profile(agent.id);
      setProfile(p);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load identity profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, [agent.id]);

  const handleSetAttribute = async () => {
    if (!newAttrKey.trim() || !newAttrValue.trim()) return;
    try {
      await api.identity.setAttribute(agent.id, newAttrKey.trim(), newAttrValue.trim(), newAttrCategory);
      toast.success(`Attribute "${newAttrKey}" set`);
      setNewAttrKey('');
      setNewAttrValue('');
      loadProfile();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleDeleteAttribute = async (key: string) => {
    try {
      await api.identity.deleteAttribute(agent.id, key);
      toast.success(`Attribute "${key}" deleted`);
      loadProfile();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleToggleLock = async (key: string, locked: boolean) => {
    try {
      if (locked) {
        await api.identity.unlockAttribute(agent.id, key);
      } else {
        await api.identity.lockAttribute(agent.id, key);
      }
      toast.success(locked ? `Attribute "${key}" unlocked` : `Attribute "${key}" locked`);
      loadProfile();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleAddPersona = async () => {
    if (!newPersonaName.trim()) return;
    try {
      await api.identity.addPersona(agent.id, {
        name: newPersonaName.trim(),
        persona_type: newPersonaType,
        description: newPersonaDesc,
        tone: newPersonaTone,
        verbosity: newPersonaVerbosity,
        expertise_areas: newPersonaExpertise.split(',').map(s => s.trim()).filter(Boolean),
      });
      toast.success(`Persona "${newPersonaName}" added`);
      setNewPersonaName('');
      setNewPersonaDesc('');
      setNewPersonaExpertise('');
      loadProfile();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleActivatePersona = async (personaName: string) => {
    try {
      await api.identity.activatePersona(agent.id, personaName);
      toast.success(`Persona "${personaName}" activated`);
      loadProfile();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  if (loading) return (
    <div className="panel-container">
      <div className="panel-loading">
        <div className="dashboard-spinner"></div>
        <div>Loading identity profile...</div>
      </div>
    </div>
  );

  if (error) return (
    <div className="panel-container">
      <div className="error-banner">
        {error}
        <button onClick={loadProfile} className="btn-sm" style={{ marginLeft: '8px' }}>Retry</button>
      </div>
    </div>
  );

  const personaTypes = ['companion', 'professional', 'creative', 'analytical', 'mentor', 'assistant'];

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Buddy Identity</h2>
          <div className="panel-subtitle">Personal AI Identity & Persona Management</div>
        </div>
      </div>

      {/* Profile Summary */}
      <div className="identity-summary-bar">
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{profile?.attributes_count || 0}</div>
          <div className="dashboard-stat-label">Attributes</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{profile?.personas?.length || 0}</div>
          <div className="dashboard-stat-label">Personas</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{profile?.total_interactions || 0}</div>
          <div className="dashboard-stat-label">Interactions</div>
        </div>
        <div className="nexus-stat-item">
          <div className="dashboard-stat-value">{profile?.active_persona || 'default'}</div>
          <div className="dashboard-stat-label">Active Persona</div>
        </div>
      </div>

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        <button
          className={`forge-tab ${activeSection === 'attributes' ? 'active' : ''}`}
          onClick={() => setActiveSection('attributes')}
        >
          Attributes
        </button>
        <button
          className={`forge-tab ${activeSection === 'personas' ? 'active' : ''}`}
          onClick={() => setActiveSection('personas')}
        >
          Personas
        </button>
        <button
          className={`forge-tab ${activeSection === 'learning' ? 'active' : ''}`}
          onClick={() => setActiveSection('learning')}
        >
          Learning
        </button>
      </div>

      {/* Attributes Section */}
      {activeSection === 'attributes' && (
        <>
          <div className="dashboard-section">
            <h3>Add Attribute</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Key</label>
                <input
                  type="text"
                  placeholder="e.g., preferred_language"
                  value={newAttrKey}
                  onChange={e => setNewAttrKey(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Value</label>
                <input
                  type="text"
                  placeholder="e.g., Python"
                  value={newAttrValue}
                  onChange={e => setNewAttrValue(e.target.value)}
                />
              </div>
            </div>
            <div className="form-group">
              <label>Category</label>
              <select value={newAttrCategory} onChange={e => setNewAttrCategory(e.target.value)}>
                <option value="preference">Preference</option>
                <option value="skill">Skill</option>
                <option value="trait">Trait</option>
                <option value="knowledge">Knowledge</option>
                <option value="behavior">Behavior</option>
              </select>
            </div>
            <button className="btn-primary btn-full" onClick={handleSetAttribute}>
              Set Attribute
            </button>
          </div>

          <div className="dashboard-section">
            <h3>Current Attributes ({profile ? Object.keys(profile.attributes || {}).length : 0})</h3>
            {profile && Object.keys(profile.attributes || {}).length > 0 ? (
              <div className="forge-skill-list">
                {Object.entries(profile.attributes).map(([key, attr]: [string, any]) => (
                  <div key={key} className="forge-skill-card">
                    <div className="forge-skill-header">
                      <div className="forge-skill-name">{attr.key}</div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <span className={`dashboard-badge ${attr.is_locked ? 'inactive' : 'active'}`}>
                          {attr.is_locked ? 'Locked' : 'Mutable'}
                        </span>
                      </div>
                    </div>
                    <div className="forge-skill-meta">
                      <div>Value: <strong>{String(attr.value)}</strong></div>
                      <div>
                        <span>Category: {attr.category}</span> ·
                        <span> Confidence: {(attr.confidence * 100).toFixed(0)}%</span> ·
                        <span> Evidence: {attr.evidence_count}</span>
                      </div>
                      <div className="text-xs text-muted">
                        Source: {attr.source} · Updated: {new Date(attr.last_updated).toLocaleString()}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                      <button
                        className="btn-sm"
                        onClick={() => handleToggleLock(key, attr.is_locked)}
                      >
                        {attr.is_locked ? 'Unlock' : 'Lock'}
                      </button>
                      <button
                        className="btn-sm btn-danger"
                        onClick={() => handleDeleteAttribute(key)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="panel-empty">No attributes set yet</div>
            )}
          </div>
        </>
      )}

      {/* Personas Section */}
      {activeSection === 'personas' && (
        <>
          <div className="dashboard-section">
            <h3>Create Persona</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  placeholder="e.g., Teacher Mode"
                  value={newPersonaName}
                  onChange={e => setNewPersonaName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={newPersonaType} onChange={e => setNewPersonaType(e.target.value)}>
                  {personaTypes.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <input
                type="text"
                placeholder="Brief description of this persona..."
                value={newPersonaDesc}
                onChange={e => setNewPersonaDesc(e.target.value)}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Tone</label>
                <select value={newPersonaTone} onChange={e => setNewPersonaTone(e.target.value)}>
                  {['professional', 'casual', 'friendly', 'formal', 'humorous', 'empathetic'].map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Verbosity</label>
                <select value={newPersonaVerbosity} onChange={e => setNewPersonaVerbosity(e.target.value)}>
                  {['minimal', 'moderate', 'verbose', 'comprehensive'].map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Expertise Areas (comma-separated)</label>
              <input
                type="text"
                placeholder="e.g., Python, Machine Learning, DevOps"
                value={newPersonaExpertise}
                onChange={e => setNewPersonaExpertise(e.target.value)}
              />
            </div>
            <button className="btn-primary btn-full" onClick={handleAddPersona}>
              Create Persona
            </button>
          </div>

          <div className="dashboard-section">
            <h3>Personas</h3>
            {profile?.personas && profile.personas.length > 0 ? (
              <div className="forge-skill-list">
                {profile.personas.map((persona, idx) => (
                  <div key={idx} className="forge-skill-card">
                    <div className="forge-skill-header">
                      <div className="forge-skill-name">
                        {persona.name}
                        {persona.is_active && (
                          <span style={{ marginLeft: '8px', fontSize: '0.7rem', color: '#10b981' }}>
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <span className={`dashboard-badge ${persona.is_active ? 'active' : 'inactive'}`}>
                        {persona.type}
                      </span>
                    </div>
                    <div className="forge-skill-meta">
                      {persona.description && <div>{persona.description}</div>}
                      <div>
                        <span>Tone: {persona.tone}</span> ·
                        <span> Verbosity: {persona.verbosity}</span>
                      </div>
                      {persona.expertise_areas.length > 0 && (
                        <div style={{ marginTop: '4px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {persona.expertise_areas.map((area: string) => (
                            <span key={area} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                              {area}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {!persona.is_active && (
                      <button
                        className="btn-sm btn-success"
                        style={{ marginTop: '8px' }}
                        onClick={() => handleActivatePersona(persona.name)}
                      >
                        Activate
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="panel-empty">No personas created yet</div>
            )}
          </div>
        </>
      )}

      {/* Learning Section */}
      {activeSection === 'learning' && (
        <div className="dashboard-section">
          <h3>Learning Insights</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.6' }}>
            The Buddy Identity system continuously learns from your interactions to build a
            personalized profile. Attributes are automatically inferred from conversations
            and can be locked to preserve important preferences.
          </p>
          <div style={{ marginTop: '16px' }}>
            <div className="dashboard-stat-row">
              <span>Total Interactions</span>
              <strong>{profile?.total_interactions || 0}</strong>
            </div>
            <div className="dashboard-stat-row">
              <span>Active Persona</span>
              <strong>{profile?.active_persona || 'default'}</strong>
            </div>
            <div className="dashboard-stat-row">
              <span>Profile Created</span>
              <strong>{profile?.created_at ? new Date(profile.created_at).toLocaleString() : 'N/A'}</strong>
            </div>
            <div className="dashboard-stat-row">
              <span>Last Updated</span>
              <strong>{profile?.updated_at ? new Date(profile.updated_at).toLocaleString() : 'N/A'}</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};