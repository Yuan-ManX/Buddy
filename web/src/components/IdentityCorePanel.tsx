import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { Agent } from '../types';
import type { IdentityCoreProfile, IdentityCoreStats, EpisodicEntry, SemanticNode, ProceduralPattern, IdentityTrait, IdentityRegistryStats } from '../types';

interface IdentityCorePanelProps {
  agent: Agent;
}

export const IdentityCorePanel: React.FC<IdentityCorePanelProps> = ({ agent }) => {
  const toast = useToast();
  const [profile, setProfile] = useState<IdentityCoreProfile | null>(null);
  const [stats, setStats] = useState<IdentityCoreStats | null>(null);
  const [registryStats, setRegistryStats] = useState<IdentityRegistryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'profile' | 'episodic' | 'semantic' | 'procedural' | 'traits'>('profile');
  const [episodicEntries, setEpisodicEntries] = useState<EpisodicEntry[]>([]);
  const [semanticNodes, setSemanticNodes] = useState<SemanticNode[]>([]);
  const [experienceForm, setExperienceForm] = useState({ content: '', importance: '0.5', emotional_valence: '0.0' });
  const [traitForm, setTraitForm] = useState({ name: '', delta: '0.05', confidence_delta: '0.01' });
  const [patternForm, setPatternForm] = useState({ pattern_type: '', trigger_conditions: '', action_sequence: '' });
  const [episodicKeyword, setEpisodicKeyword] = useState('');
  const [semanticConcept, setSemanticConcept] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [p, r] = await Promise.all([
        api.identityCore.profile(agent.id),
        api.identityCore.stats(),
      ]);
      setProfile(p);
      setStats(r.identities[agent.id] || null);
      setRegistryStats(r);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load identity core data');
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => { loadData(); }, [loadData]);

  const loadEpisodic = async () => {
    try {
      const result = await api.identityCore.episodic(agent.id, episodicKeyword || undefined);
      setEpisodicEntries(result.entries);
    } catch (e: any) { toast.error(e.message); }
  };

  const loadSemantic = async () => {
    try {
      const result = await api.identityCore.semantic(agent.id, semanticConcept || undefined);
      setSemanticNodes(result.nodes);
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRecordExperience = async () => {
    if (!experienceForm.content.trim()) return;
    try {
      await api.identityCore.recordExperience(agent.id, {
        content: experienceForm.content,
        importance: parseFloat(experienceForm.importance),
        emotional_valence: parseFloat(experienceForm.emotional_valence),
        agent_name: agent.name,
      });
      toast.success('Experience recorded');
      setExperienceForm({ content: '', importance: '0.5', emotional_valence: '0.0' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleUpdateTrait = async () => {
    if (!traitForm.name.trim()) return;
    try {
      await api.identityCore.updateTrait(agent.id, {
        name: traitForm.name,
        delta: parseFloat(traitForm.delta),
        confidence_delta: parseFloat(traitForm.confidence_delta),
      });
      toast.success('Trait updated');
      setTraitForm({ name: '', delta: '0.05', confidence_delta: '0.01' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleLearnPattern = async () => {
    if (!patternForm.pattern_type.trim()) return;
    try {
      await api.identityCore.learnPattern(agent.id, {
        pattern_type: patternForm.pattern_type,
        trigger_conditions: patternForm.trigger_conditions.split(',').map(s => s.trim()).filter(Boolean),
        action_sequence: patternForm.action_sequence.split(',').map(s => s.trim()).filter(Boolean),
      });
      toast.success('Pattern learned');
      setPatternForm({ pattern_type: '', trigger_conditions: '', action_sequence: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const traitCategoryColors: Record<string, string> = {
    cognitive: '#3b82f6', behavioral: '#8b5cf6', social: '#ec4899', domain: '#06b6d4', preference: '#f59e0b',
  };

  const valenceColor = (v: number) => {
    if (v > 0.3) return '#22c55e';
    if (v < -0.3) return '#ef4444';
    return '#9ca3af';
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Identity Core</h2>
          <p className="panel-subtitle">Hierarchical Memory Modeling for agent identity</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading identity data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Identity Core</h2>
        <p className="panel-subtitle">HMM — Episodic, Semantic, Procedural memory layers</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{marginLeft: 8}}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{(stats.self_awareness * 100).toFixed(0)}%</span><span className="stat-label">Self-Awareness</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{(stats.identity_coherence * 100).toFixed(0)}%</span><span className="stat-label">Coherence</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_experiences}</span><span className="stat-label">Experiences</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_traits}</span><span className="stat-label">Traits</span></div></div>
        </div>
      )}

      {/* Memory Layer Stats */}
      {stats && (
        <div className="stats-bar" style={{marginTop: 0}}>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.episodic_entries}</span><span className="stat-label">Episodic</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.semantic_nodes}</span><span className="stat-label">Semantic</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.procedural_patterns}</span><span className="stat-label">Procedural</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_abstractions}</span><span className="stat-label">Abstractions</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['profile', 'episodic', 'semantic', 'procedural', 'traits'] as const).map(s => (
          <button key={s} className={`forge-tab ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Profile */}
      {activeSection === 'profile' && profile && (
        <div className="dashboard-section">
          <h3>Identity Overview</h3>
          <div className="dashboard-stat-row"><span>Agent ID</span><strong>{profile.agent_id}</strong></div>
          <div className="dashboard-stat-row"><span>Self-Awareness</span><strong>{(profile.self_awareness * 100).toFixed(1)}%</strong></div>
          <div className="dashboard-stat-row"><span>Identity Coherence</span><strong>{(profile.identity_coherence * 100).toFixed(1)}%</strong></div>
          <div className="dashboard-stat-row"><span>Episodic Entries</span><strong>{profile.memory_stats.episodic_entries}</strong></div>
          <div className="dashboard-stat-row"><span>Semantic Nodes</span><strong>{profile.memory_stats.semantic_nodes}</strong></div>
          <div className="dashboard-stat-row"><span>Procedural Patterns</span><strong>{profile.memory_stats.procedural_patterns}</strong></div>
          <div className="dashboard-stat-row"><span>Total Experiences</span><strong>{profile.memory_stats.total_experiences}</strong></div>
          <div className="dashboard-stat-row"><span>Total Abstractions</span><strong>{profile.memory_stats.total_abstractions}</strong></div>

          <h3 style={{marginTop: 20}}>Record Experience</h3>
          <div className="form-group">
            <label>Content</label>
            <textarea rows={3} value={experienceForm.content} onChange={e => setExperienceForm(f => ({...f, content: e.target.value}))} placeholder="Describe what happened..." />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Importance (0-1)</label>
              <input type="text" value={experienceForm.importance} onChange={e => setExperienceForm(f => ({...f, importance: e.target.value}))} />
            </div>
            <div className="form-group">
              <label>Emotional Valence (-1 to 1)</label>
              <input type="text" value={experienceForm.emotional_valence} onChange={e => setExperienceForm(f => ({...f, emotional_valence: e.target.value}))} />
            </div>
          </div>
          <button className="btn-primary" onClick={handleRecordExperience}>Record Experience</button>

          {registryStats && (
            <div style={{marginTop: 20}}>
              <h3>All Agent Identities</h3>
              <div className="dashboard-stat-row"><span>Total Identities</span><strong>{registryStats.total_identities}</strong></div>
              {Object.entries(registryStats.identities).map(([aid, istats]) => (
                <div key={aid} className="forge-skill-card" style={{marginBottom: 8}}>
                  <div className="forge-skill-header"><div className="forge-skill-name">{istats.agent_name} ({aid})</div><span className="dashboard-badge active">{(istats.self_awareness * 100).toFixed(0)}% aware</span></div>
                  <div className="forge-skill-meta">
                    <div>Experiences: {istats.total_experiences} | Traits: {istats.total_traits} | Patterns: {istats.procedural_patterns}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Episodic Memory */}
      {activeSection === 'episodic' && (
        <div className="dashboard-section">
          <h3>Episodic Memory</h3>
          <div className="form-row">
            <div className="form-group" style={{flex: 1}}>
              <label>Keyword Search</label>
              <input type="text" value={episodicKeyword} onChange={e => setEpisodicKeyword(e.target.value)} placeholder="Search experiences..." />
            </div>
            <div className="form-group" style={{alignSelf: 'flex-end'}}>
              <button className="btn-primary" onClick={loadEpisodic}>Search</button>
            </div>
          </div>

          {episodicEntries.length === 0 ? (
            <div className="panel-empty">No episodic entries found. Record experiences first.</div>
          ) : (
            <div className="forge-skill-list">
              {episodicEntries.map(e => (
                <div key={e.entry_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{fontSize: '0.9rem'}}>{e.content}</div>
                    <div style={{display: 'flex', gap: 4}}>
                      <span className="dashboard-badge" style={{background: '#f3f4f6', color: '#374151'}}>{(e.importance * 100).toFixed(0)}%</span>
                      <span className="dashboard-badge" style={{background: valenceColor(e.emotional_valence), color: '#fff'}}>{e.emotional_valence > 0 ? '+' : ''}{e.emotional_valence.toFixed(2)}</span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>{new Date(e.timestamp).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Semantic Memory */}
      {activeSection === 'semantic' && (
        <div className="dashboard-section">
          <h3>Semantic Knowledge</h3>
          <div className="form-row">
            <div className="form-group" style={{flex: 1}}>
              <label>Concept Search</label>
              <input type="text" value={semanticConcept} onChange={e => setSemanticConcept(e.target.value)} placeholder="Search concepts..." />
            </div>
            <div className="form-group" style={{alignSelf: 'flex-end'}}>
              <button className="btn-primary" onClick={loadSemantic}>Search</button>
            </div>
          </div>

          {semanticNodes.length === 0 ? (
            <div className="panel-empty">No semantic nodes found. Record more experiences to build knowledge.</div>
          ) : (
            <div className="forge-skill-list">
              {semanticNodes.map(n => (
                <div key={n.node_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{n.concept}</div>
                    <span className="dashboard-badge" style={{background: '#3b82f6', color: '#fff'}}>{(n.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Relationships: {Object.keys(n.relationships).join(', ') || 'None'}</div>
                    <div>Sources: {n.source_episodes.length} episodes</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Procedural Memory */}
      {activeSection === 'procedural' && (
        <div className="dashboard-section">
          <h3>Procedural Patterns</h3>
          <div className="skill-execute" style={{marginBottom: 16, position: 'static'}}>
            <h3>Learn New Pattern</h3>
            <div className="form-group">
              <label>Pattern Type</label>
              <input type="text" value={patternForm.pattern_type} onChange={e => setPatternForm(f => ({...f, pattern_type: e.target.value}))} placeholder="e.g., code_review" />
            </div>
            <div className="form-group">
              <label>Trigger Conditions (comma-separated)</label>
              <input type="text" value={patternForm.trigger_conditions} onChange={e => setPatternForm(f => ({...f, trigger_conditions: e.target.value}))} placeholder="review_request, pull_request" />
            </div>
            <div className="form-group">
              <label>Action Sequence (comma-separated)</label>
              <input type="text" value={patternForm.action_sequence} onChange={e => setPatternForm(f => ({...f, action_sequence: e.target.value}))} placeholder="read_code, analyze, suggest" />
            </div>
            <button className="btn-primary" onClick={handleLearnPattern}>Learn Pattern</button>
          </div>
        </div>
      )}

      {/* Traits */}
      {activeSection === 'traits' && stats && (
        <div className="dashboard-section">
          <h3>Identity Traits</h3>
          <div className="skill-execute" style={{marginBottom: 16, position: 'static'}}>
            <h3>Update Trait</h3>
            <div className="form-row">
              <div className="form-group" style={{flex: 2}}>
                <label>Trait Name</label>
                <input type="text" value={traitForm.name} onChange={e => setTraitForm(f => ({...f, name: e.target.value}))} placeholder="e.g., helpfulness" />
              </div>
              <div className="form-group">
                <label>Delta</label>
                <input type="text" value={traitForm.delta} onChange={e => setTraitForm(f => ({...f, delta: e.target.value}))} placeholder="0.05" />
              </div>
              <div className="form-group">
                <label>Confidence Delta</label>
                <input type="text" value={traitForm.confidence_delta} onChange={e => setTraitForm(f => ({...f, confidence_delta: e.target.value}))} placeholder="0.01" />
              </div>
            </div>
            <button className="btn-primary" onClick={handleUpdateTrait}>Update Trait</button>
          </div>

          {Object.entries(stats.traits).map(([name, trait]) => (
            <div key={name} className="forge-skill-card" style={{marginBottom: 8}}>
              <div className="forge-skill-header">
                <div className="forge-skill-name">{name}</div>
                <span className="dashboard-badge" style={{background: traitCategoryColors[trait.category] || '#666', color: '#fff'}}>{trait.category}</span>
              </div>
              <div className="forge-skill-meta">
                <div className="dashboard-stat-row">
                  <span>Value</span>
                  <div style={{width: 120, background: '#e5e7eb', borderRadius: 3, height: 8, marginLeft: 8}}>
                    <div style={{width: `${trait.value * 100}%`, background: '#3b82f6', height: '100%', borderRadius: 3}} />
                  </div>
                  <strong style={{marginLeft: 8}}>{(trait.value * 100).toFixed(0)}%</strong>
                </div>
                <div className="dashboard-stat-row">
                  <span>Confidence</span>
                  <strong>{(trait.confidence * 100).toFixed(0)}%</strong>
                </div>
                <div className="dashboard-stat-row">
                  <span>Stability</span>
                  <strong>{(trait.stability * 100).toFixed(0)}%</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default IdentityCorePanel;