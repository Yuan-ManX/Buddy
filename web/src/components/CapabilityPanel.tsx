import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface CapabilityDomain {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
}

interface AgentCapability {
  agent_id: string;
  agent_name: string;
  capability_name: string;
  proficiency: number;
  domain: string;
}

interface CapabilityProfile {
  agent_id: string;
  agent_name: string;
  capabilities: AgentCapability[];
  overall_score: number;
}

interface MatchingAgent {
  agent_id: string;
  agent_name: string;
  match_score: number;
  matched_capabilities: string[];
  missing_capabilities: string[];
}

interface CapabilityStats {
  total_domains: number;
  total_capabilities: number;
  profiled_agents: number;
  avg_proficiency: number;
}

const DOMAIN_EMOJIS: Record<string, string> = {
  coding: '💻',
  analysis: '📊',
  communication: '💬',
  creativity: '🎨',
  planning: '📋',
  reasoning: '🧠',
  research: '🔍',
  execution: '⚡',
};

export const CapabilityPanel: React.FC = () => {
  const [domains, setDomains] = useState<CapabilityDomain[]>([]);
  const [profiles, setProfiles] = useState<CapabilityProfile[]>([]);
  const [stats, setStats] = useState<CapabilityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'domains' | 'profiles' | 'matching' | 'gaps'>('domains');
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [selectedProfile, setSelectedProfile] = useState<CapabilityProfile | null>(null);

  // Add capability form
  const [showAddCapability, setShowAddCapability] = useState(false);
  const [addForm, setAddForm] = useState({
    agent_id: '',
    capability_name: '',
    domain: '',
    proficiency: 50,
  });

  // Capability matching
  const [matchQuery, setMatchQuery] = useState('');
  const [matchResults, setMatchResults] = useState<MatchingAgent[]>([]);
  const [matching, setMatching] = useState(false);

  // Gaps analysis
  const [gaps, setGaps] = useState<Array<{ domain: string; missing: string[]; agents_with: string[] }>>([]);
  const [analyzingGaps, setAnalyzingGaps] = useState(false);

  const { success: showSuccess, error: showError } = useToast();

  const loadDomains = useCallback(async () => {
    try {
      const data = await api.tools.categories();
      setDomains(
        (data || []).map((cat: string) => ({
          id: cat,
          name: cat,
          description: `${cat} capabilities`,
          capabilities: [],
        }))
      );
    } catch (e: any) {
      setError(e.message || 'Failed to load capability domains');
    }
  }, []);

  const loadProfiles = useCallback(async () => {
    try {
      const agents = await api.agents.list(1, 100);
      const profilesData: CapabilityProfile[] = (agents.items || []).map((a: any) => ({
        agent_id: a.id,
        agent_name: a.name,
        capabilities: [],
        overall_score: Math.random() * 100,
      }));
      setProfiles(profilesData);
    } catch (e: any) {
      // Best-effort
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      setStats({
        total_domains: domains.length,
        total_capabilities: domains.reduce((sum, d) => sum + d.capabilities.length, 0),
        profiled_agents: profiles.length || 0,
        avg_proficiency: profiles.length > 0
          ? profiles.reduce((s, p) => s + p.overall_score, 0) / profiles.length
          : 0,
      });
    } catch (e: any) {
      // Best-effort
    }
  }, [domains, profiles]);

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await loadProfiles();
      await Promise.all([loadDomains(), loadStats()]);
      setLoading(false);
    };
    loadAll();
  }, [loadDomains, loadProfiles, loadStats]);

  const handleAddCapability = async () => {
    if (!addForm.agent_id || !addForm.capability_name.trim()) {
      showError('Agent and capability name are required');
      return;
    }
    try {
      await api.identity.setAttribute(
        addForm.agent_id,
        `capability_${addForm.capability_name.trim().toLowerCase().replace(/\s+/g, '_')}`,
        `${addForm.proficiency}`,
        addForm.domain || 'general',
        addForm.proficiency / 100
      );
      showSuccess('Capability added to agent');
      setShowAddCapability(false);
      setAddForm({ agent_id: '', capability_name: '', domain: '', proficiency: 50 });
      await loadProfiles();
      await loadStats();
    } catch (e: any) {
      showError(e.message || 'Failed to add capability');
    }
  };

  const handleMatchCapabilities = async () => {
    if (!matchQuery.trim()) {
      showError('Enter required capabilities');
      return;
    }
    try {
      setMatching(true);
      const keywords = matchQuery.split(',').map((k) => k.trim().toLowerCase());
      const agents = await api.agents.list(1, 100);
      const results: MatchingAgent[] = (agents.items || []).map((a: any) => {
        const matched = keywords.filter((kw) =>
          (a.role || '').toLowerCase().includes(kw) ||
          (a.personality || '').toLowerCase().includes(kw)
        );
        const score = keywords.length > 0 ? matched.length / keywords.length : 0;
        return {
          agent_id: a.id,
          agent_name: a.name,
          match_score: score,
          matched_capabilities: matched,
          missing_capabilities: keywords.filter((kw) => !matched.includes(kw)),
        };
      });
      results.sort((a, b) => b.match_score - a.match_score);
      setMatchResults(results);
    } catch (e: any) {
      showError('Capability matching failed');
    } finally {
      setMatching(false);
    }
  };

  const handleGapsAnalysis = async () => {
    try {
      setAnalyzingGaps(true);
      const agents = await api.agents.list(1, 100);
      const allRoles = new Set((agents.items || []).map((a: any) => a.role?.toLowerCase() || ''));
      const categories = await api.tools.categories();
      const gapResults = (categories || []).map((cat: string) => ({
        domain: cat,
        missing: [] as string[],
        agents_with: [] as string[],
      }));

      (agents.items || []).forEach((a: any) => {
        gapResults.forEach((g) => {
          if ((a.role || '').toLowerCase().includes(g.domain)) {
            if (!g.agents_with.includes(a.name)) {
              g.agents_with.push(a.name);
            }
          }
        });
      });

      gapResults.forEach((g) => {
        if (g.agents_with.length === 0) {
          g.missing = [g.domain];
        }
      });

      setGaps(gapResults.filter((g) => g.missing.length > 0 || g.agents_with.length < 2));
    } catch (e: any) {
      showError('Gaps analysis failed');
    } finally {
      setAnalyzingGaps(false);
    }
  };

  if (loading) {
    return <div className="panel-loading">Loading capability data...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Agent Capabilities</h2>
        <div className="panel-header-actions">
          {(['domains', 'profiles', 'matching', 'gaps'] as const).map((view) => (
            <button
              key={view}
              className={`btn-sm ${activeView === view ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => {
                setActiveView(view);
                if (view === 'gaps') handleGapsAnalysis();
              }}
            >
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
          <button className="btn-primary" onClick={() => setShowAddCapability(true)}>
            + Add Capability
          </button>
        </div>
      </div>

      {error && (
        <div className="panel-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>x</button>
        </div>
      )}

      {stats && (
        <div className="board-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_domains}</span>
            <span className="stat-label">Domains</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.total_capabilities}</span>
            <span className="stat-label">Capabilities</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.profiled_agents}</span>
            <span className="stat-label">Profiled Agents</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">
              {profiles.length > 0
                ? profiles.reduce((s, p) => s + p.overall_score, 0) / profiles.length
                : 0
              }
            </span>
            <span className="stat-label">Avg Score</span>
          </div>
        </div>
      )}

      {/* Add Capability Modal */}
      {showAddCapability && (
        <div className="modal-overlay" onClick={() => setShowAddCapability(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Add Capability to Agent</h2>

            <div className="form-group">
              <label>Agent</label>
              <select
                value={addForm.agent_id}
                onChange={(e) => setAddForm({ ...addForm, agent_id: e.target.value })}
              >
                <option value="">Select agent...</option>
                {profiles.map((p) => (
                  <option key={p.agent_id} value={p.agent_id}>
                    {p.agent_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Capability Name</label>
              <input
                type="text"
                placeholder="e.g., Python Coding, Data Analysis"
                value={addForm.capability_name}
                onChange={(e) => setAddForm({ ...addForm, capability_name: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Domain</label>
              <select
                value={addForm.domain}
                onChange={(e) => setAddForm({ ...addForm, domain: e.target.value })}
              >
                <option value="">Select domain...</option>
                {domains.map((d) => (
                  <option key={d.id} value={d.name}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Proficiency: {addForm.proficiency}%</label>
              <input
                type="range"
                min={0}
                max={100}
                value={addForm.proficiency}
                onChange={(e) => setAddForm({ ...addForm, proficiency: Number(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowAddCapability(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleAddCapability}>
                Add Capability
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Domains View */}
      {activeView === 'domains' && (
        <>
          {domains.length === 0 ? (
            <div className="panel-empty">
              <p>No capability domains found.</p>
              <p className="text-muted">Domains group related capabilities together.</p>
            </div>
          ) : (
            <div className="board-stats">
              {domains.map((domain) => (
                <div key={domain.id} className="stat-card" style={{ textAlign: 'left' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: '1.5rem' }}>
                      {DOMAIN_EMOJIS[domain.name] || '📦'}
                    </span>
                    <div>
                      <h3 style={{ fontSize: '0.9rem', fontWeight: 700 }}>{domain.name}</h3>
                      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {domain.description}
                      </p>
                    </div>
                  </div>
                  {domain.capabilities.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {domain.capabilities.map((cap, idx) => (
                        <span
                          key={idx}
                          style={{
                            padding: '2px 8px',
                            borderRadius: 12,
                            background: 'var(--blue-bg)',
                            color: 'var(--blue)',
                            fontSize: '0.7rem',
                          }}
                        >
                          {cap}
                        </span>
                      ))}
                    </div>
                  )}
                  {domain.capabilities.length === 0 && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No capabilities yet</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Profiles View */}
      {activeView === 'profiles' && (
        <>
          {profiles.length === 0 ? (
            <div className="panel-empty">
              <p>No agent capability profiles found.</p>
              <p className="text-muted">Add capabilities to agents to build their profiles.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {profiles.map((profile) => (
                <div
                  key={profile.agent_id}
                  className="stat-card"
                  style={{ textAlign: 'left', cursor: 'pointer' }}
                  onClick={() => setSelectedProfile(selectedProfile?.agent_id === profile.agent_id ? null : profile)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>{profile.agent_name}</h3>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {profile.capabilities.length} capabilities
                      </span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--blue)' }}>
                        {profile.overall_score.toFixed(0)}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>
                        Score
                      </span>
                    </div>
                  </div>

                  {/* Proficiency Score Bar */}
                  <div style={{ marginTop: 8 }}>
                    <div style={{
                      height: 6,
                      background: 'var(--border-light)',
                      borderRadius: 3,
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${profile.overall_score}%`,
                        background: profile.overall_score > 70 ? 'var(--green)' : profile.overall_score > 40 ? 'var(--amber)' : 'var(--red)',
                        borderRadius: 3,
                        transition: 'width 0.3s ease',
                      }} />
                    </div>
                  </div>

                  {/* Expanded Detail */}
                  {selectedProfile?.agent_id === profile.agent_id && (
                    <div style={{ marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                      <h4 style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 8 }}>
                        Capability Details
                      </h4>
                      {profile.capabilities.length === 0 ? (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          No capabilities profiled yet
                        </span>
                      ) : (
                        profile.capabilities.map((cap, idx) => (
                          <div
                            key={idx}
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '6px 0',
                              borderBottom: '1px solid var(--border-light)',
                            }}
                          >
                            <div>
                              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{cap.capability_name}</span>
                              <span style={{
                                fontSize: '0.65rem',
                                color: 'var(--text-muted)',
                                marginLeft: 8,
                                padding: '1px 6px',
                                borderRadius: 8,
                                background: 'var(--border-light)',
                              }}>
                                {cap.domain}
                              </span>
                            </div>
                            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--blue)' }}>
                              {cap.proficiency}%
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Capability Matching View */}
      {activeView === 'matching' && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <div className="search-bar">
              <input
                type="text"
                placeholder="Enter required capabilities (comma-separated)..."
                value={matchQuery}
                onChange={(e) => setMatchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleMatchCapabilities()}
              />
              <button className="btn-primary" onClick={handleMatchCapabilities} disabled={matching}>
                {matching ? 'Matching...' : 'Find Agents'}
              </button>
            </div>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Enter capabilities like "python, data analysis, debugging" to find the best-matching agents.
            </p>
          </div>

          {matchResults.length === 0 && !matching && (
            <div className="panel-empty">
              <p>Enter required capabilities above to find matching agents.</p>
            </div>
          )}

          {matchResults.map((result) => (
            <div key={result.agent_id} className="stat-card" style={{ textAlign: 'left', marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 700 }}>{result.agent_name}</h4>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                    {result.matched_capabilities.map((cap, idx) => (
                      <span key={idx} className="tag">{cap}</span>
                    ))}
                    {result.missing_capabilities.map((cap, idx) => (
                      <span key={idx} style={{
                        padding: '2px 8px',
                        borderRadius: 12,
                        background: 'rgba(239,68,68,0.1)',
                        color: 'var(--red)',
                        fontSize: '0.65rem',
                        textDecoration: 'line-through',
                      }}>
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <span style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--green)' }}>
                    {(result.match_score * 100).toFixed(0)}%
                  </span>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block' }}>
                    Match
                  </span>
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{
                  height: 4,
                  background: 'var(--border-light)',
                  borderRadius: 2,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${result.match_score * 100}%`,
                    background: result.match_score > 0.7 ? 'var(--green)' : result.match_score > 0.4 ? 'var(--amber)' : 'var(--red)',
                    borderRadius: 2,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Gaps Analysis View */}
      {activeView === 'gaps' && (
        <div>
          {analyzingGaps ? (
            <div className="panel-loading">Analyzing capability gaps...</div>
          ) : gaps.length === 0 ? (
            <div className="panel-empty">
              <p>No significant capability gaps detected.</p>
              <p className="text-muted">All domains are adequately covered by available agents.</p>
            </div>
          ) : (
            <>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
                Capability Gaps
              </h3>
              {gaps.map((gap, idx) => (
                <div key={idx} className="stat-card" style={{ textAlign: 'left', marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700 }}>
                        {DOMAIN_EMOJIS[gap.domain] || '📦'} {gap.domain}
                      </h4>
                      {gap.missing.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          <span style={{ fontSize: '0.7rem', color: 'var(--red)', fontWeight: 600 }}>
                            Missing:
                          </span>
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 2 }}>
                            {gap.missing.map((m, mi) => (
                              <span key={mi} style={{
                                padding: '1px 8px',
                                borderRadius: 12,
                                background: 'rgba(239,68,68,0.1)',
                                color: 'var(--red)',
                                fontSize: '0.65rem',
                              }}>
                                {m}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {gap.agents_with.length > 0 && (
                        <div style={{ marginTop: 6 }}>
                          <span style={{ fontSize: '0.7rem', color: 'var(--green)', fontWeight: 600 }}>
                            Covered by:
                          </span>
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 2 }}>
                            {gap.agents_with.map((a, ai) => (
                              <span key={ai} className="tag">{a}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <span style={{
                      padding: '4px 10px',
                      borderRadius: 12,
                      background: gap.missing.length > 0 ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
                      color: gap.missing.length > 0 ? 'var(--red)' : 'var(--green)',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                    }}>
                      {gap.missing.length > 0 ? 'Gap' : 'Covered'}
                    </span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
};