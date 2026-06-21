import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

interface Profile {
  profile_id: string;
  name: string;
  display_name: string;
  description: string;
  communication_style: string;
  traits: { name: string; value: number; description: string; category: string }[];
  knowledge_domains: { domain_id: string; name: string; expertise: string; topics: string[]; confidence: number }[];
  languages: string[];
  preferred_mode: string;
  supported_modes: string[];
  version: number;
  tags: string[];
}

export const ProfilePanel: React.FC = () => {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createStyle, setCreateStyle] = useState('friendly');
  const [createDescription, setCreateDescription] = useState('');

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.profile.list();
      setProfiles(res.profiles || []);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadProfiles(); }, [loadProfiles]);

  const handleCreate = async () => {
    if (!createName.trim()) return;
    try {
      await api.profile.create({
        name: createName.trim().toLowerCase().replace(/\s+/g, '_'),
        display_name: createName.trim(),
        description: createDescription,
        communication_style: createStyle,
      });
      setShowCreate(false);
      setCreateName('');
      setCreateDescription('');
      loadProfiles();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (profileId: string) => {
    if (!confirm('Delete this profile?')) return;
    try {
      await api.profile.delete(profileId);
      setSelectedProfile(null);
      loadProfiles();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleGeneratePrompt = async (profileId: string) => {
    try {
      const res = await api.profile.generatePrompt(profileId);
      alert(`System Prompt Generated:\n\n${res.prompt}`);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const styleOptions = ['formal', 'casual', 'technical', 'friendly', 'concise', 'elaborate', 'socratic', 'direct'];
  const templateOptions = [
    { label: 'Strategist', value: 'create_strategist_template' },
    { label: 'Engineer', value: 'create_engineer_template' },
    { label: 'Companion', value: 'create_companion_template' },
    { label: 'Researcher', value: 'create_researcher_template' },
  ];

  const handleCreateTemplate = async (template: string) => {
    try {
      await api.profile.createTemplate(template);
      loadProfiles();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="profile-panel">
      <div className="panel-header">
        <h2>Profile Manager</h2>
        <span className="panel-subtitle">Agent Persona & Profile Management</span>
      </div>

      {error && <div className="panel-error">{error}<button onClick={() => setError(null)}>Dismiss</button></div>}

      <div className="panel-actions">
        <button className="btn-primary" onClick={() => setShowCreate(true)}>+ New Profile</button>
        <div className="template-buttons">
          {templateOptions.map(t => (
            <button key={t.value} className="btn-secondary" onClick={() => handleCreateTemplate(t.value)}>
              {t.label} Template
            </button>
          ))}
        </div>
      </div>

      {showCreate && (
        <div className="create-form">
          <h3>Create Profile</h3>
          <input
            className="input"
            placeholder="Profile name"
            value={createName}
            onChange={e => setCreateName(e.target.value)}
          />
          <select className="input" value={createStyle} onChange={e => setCreateStyle(e.target.value)}>
            {styleOptions.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <textarea
            className="input"
            placeholder="Description"
            value={createDescription}
            onChange={e => setCreateDescription(e.target.value)}
            rows={2}
          />
          <div className="form-actions">
            <button className="btn-primary" onClick={handleCreate}>Create</button>
            <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="profile-list">
        {loading && <div className="loading">Loading profiles...</div>}
        {profiles.map(p => (
          <div
            key={p.profile_id}
            className={`profile-card ${selectedProfile?.profile_id === p.profile_id ? 'selected' : ''}`}
            onClick={() => setSelectedProfile(p)}
          >
            <div className="profile-card-header">
              <span className="profile-name">{p.display_name}</span>
              <span className="profile-version">v{p.version}</span>
            </div>
            <div className="profile-card-meta">
              <span className="profile-style">{p.communication_style}</span>
              <span className="profile-traits">{p.traits.length} traits</span>
              <span className="profile-domains">{p.knowledge_domains.length} domains</span>
            </div>
          </div>
        ))}
      </div>

      {selectedProfile && (
        <div className="profile-detail">
          <h3>{selectedProfile.display_name}</h3>
          <p className="profile-description">{selectedProfile.description}</p>

          <div className="detail-section">
            <h4>Communication Style</h4>
            <span className="badge">{selectedProfile.communication_style}</span>
          </div>

          <div className="detail-section">
            <h4>Personality Traits</h4>
            <div className="trait-list">
              {selectedProfile.traits.map(t => (
                <div key={t.name} className="trait-bar">
                  <div className="trait-label">
                    <span>{t.name}</span>
                    <span>{Math.round(t.value * 100)}%</span>
                  </div>
                  <div className="trait-track">
                    <div className="trait-fill" style={{ width: `${t.value * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <h4>Knowledge Domains</h4>
            {selectedProfile.knowledge_domains.map(d => (
              <div key={d.domain_id} className="domain-card">
                <div className="domain-header">
                  <span className="domain-name">{d.name}</span>
                  <span className="badge">{d.expertise}</span>
                </div>
                {d.topics.length > 0 && (
                  <div className="domain-topics">
                    {d.topics.map(t => <span key={t} className="topic-tag">{t}</span>)}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="detail-section">
            <h4>Supported Modes</h4>
            <div className="mode-list">
              {selectedProfile.supported_modes.map(m => (
                <span key={m} className="badge mode-badge">{m}</span>
              ))}
            </div>
          </div>

          <div className="detail-actions">
            <button className="btn-primary" onClick={() => handleGeneratePrompt(selectedProfile.profile_id)}>
              Generate System Prompt
            </button>
            <button className="btn-danger" onClick={() => handleDelete(selectedProfile.profile_id)}>
              Delete Profile
            </button>
          </div>
        </div>
      )}
    </div>
  );
};