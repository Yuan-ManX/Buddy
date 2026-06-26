import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// ── Inline Types ──

interface TeamPattern {
  name: string;
  description: string;
  category: string;
  agent_count: number;
  complexity: string;
  scale: string;
  use_cases: string[];
}

interface TeamMember {
  agent_id: string;
  role: string;
  name: string;
  responsibilities: string[];
}

interface TeamArchitecture {
  team_id: string;
  team_name: string;
  domain_description: string;
  pattern: string;
  agent_count: number;
  complexity: string;
  members: TeamMember[];
  status: string;
  validation_score: number | null;
  validation_issues: string[];
  created_at: string;
  updated_at: string;
}

interface TeamArchitectStats {
  total_teams: number;
  active_teams: number;
  total_patterns: number;
  patterns_used: Record<string, number>;
  average_agent_count: number;
  average_validation_score: number;
  total_validations: number;
  total_evolutions: number;
}

// ── Pattern Config ──

const PATTERN_NAMES = [
  'Pipeline',
  'Fan-out/Fan-in',
  'Expert Pool',
  'Producer-Reviewer',
  'Supervisor',
  'Hierarchical',
];

const PATTERN_COLORS: Record<string, string> = {
  'Pipeline': '#4f6ef7',
  'Fan-out/Fan-in': '#22c55e',
  'Expert Pool': '#f59e0b',
  'Producer-Reviewer': '#8b5cf6',
  'Supervisor': '#ef4444',
  'Hierarchical': '#06b6d4',
};

const COMPLEXITY_OPTIONS = ['low', 'medium', 'high', 'very_high'];
const SCALE_OPTIONS = ['small', 'medium', 'large', 'enterprise'];

export const TeamArchitectPanel: React.FC = () => {
  const toast = useToast();

  // ── State ──
  const [stats, setStats] = useState<TeamArchitectStats | null>(null);
  const [patterns, setPatterns] = useState<TeamPattern[]>([]);
  const [teams, setTeams] = useState<TeamArchitecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'generate' | 'teams' | 'patterns' | 'evolve'>('overview');

  // Generate form
  const [generateForm, setGenerateForm] = useState({
    domain_description: '',
    team_name: '',
    preferred_pattern: '',
    agent_count: 4,
    complexity: 'medium',
    scale: 'medium',
  });
  const [analyzeResult, setAnalyzeResult] = useState<any>(null);
  const [generating, setGenerating] = useState(false);

  // Selected team detail
  const [selectedTeam, setSelectedTeam] = useState<TeamArchitecture | null>(null);
  const [teamDetailLoading, setTeamDetailLoading] = useState(false);

  // Evolve form
  const [evolveForm, setEvolveForm] = useState({
    team_id: '',
    changes: '',
    success_metrics: '',
    lessons_learned: '',
    agent_adjustments: '',
  });
  const [evolving, setEvolving] = useState(false);

  // Pattern detail
  const [selectedPattern, setSelectedPattern] = useState<TeamPattern | null>(null);
  const [patternDetailLoading, setPatternDetailLoading] = useState(false);

  // ── Data Loading ──

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, p, t] = await Promise.all([
        fetch('/api/team-architect/stats').then(r => r.ok ? r.json() : null),
        fetch('/api/team-architect/patterns').then(r => r.ok ? r.json() : Promise.reject('Failed to load patterns')),
        fetch('/api/team-architect/teams').then(r => r.ok ? r.json() : Promise.reject('Failed to load teams')),
      ]);
      setStats(s || null);
      setPatterns(p.patterns || p || []);
      setTeams(t.teams || t || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load team architect data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // ── Handlers ──

  const handleAnalyze = async () => {
    if (!generateForm.domain_description.trim()) return;
    try {
      setGenerating(true);
      const body: Record<string, unknown> = {
        domain_description: generateForm.domain_description,
        team_name: generateForm.team_name || undefined,
      };
      if (generateForm.preferred_pattern) body.preferred_pattern = generateForm.preferred_pattern;
      if (generateForm.agent_count) body.agent_count = generateForm.agent_count;
      if (generateForm.complexity) body.complexity = generateForm.complexity;
      if (generateForm.scale) body.scale = generateForm.scale;
      const res = await fetch('/api/team-architect/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Analysis failed');
      const data = await res.json();
      setAnalyzeResult(data);
      toast.success('Domain analysis complete');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerate = async () => {
    if (!generateForm.domain_description.trim()) return;
    try {
      setGenerating(true);
      const body: Record<string, unknown> = {
        domain_description: generateForm.domain_description,
        team_name: generateForm.team_name || undefined,
      };
      if (generateForm.preferred_pattern) body.preferred_pattern = generateForm.preferred_pattern;
      if (generateForm.agent_count) body.agent_count = generateForm.agent_count;
      if (generateForm.complexity) body.complexity = generateForm.complexity;
      if (generateForm.scale) body.scale = generateForm.scale;
      const res = await fetch('/api/team-architect/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Generation failed');
      const data = await res.json();
      toast.success(`Team "${data.team_name || 'Untitled'}" generated successfully`);
      setGenerateForm({
        domain_description: '',
        team_name: '',
        preferred_pattern: '',
        agent_count: 4,
        complexity: 'medium',
        scale: 'medium',
      });
      setAnalyzeResult(null);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleViewTeam = async (teamId: string) => {
    try {
      setTeamDetailLoading(true);
      const res = await fetch(`/api/team-architect/teams/${teamId}`);
      if (!res.ok) throw new Error('Failed to load team');
      const data = await res.json();
      setSelectedTeam(data);
      setActiveSection('teams');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setTeamDetailLoading(false);
    }
  };

  const handleValidateTeam = async (teamId: string) => {
    try {
      const res = await fetch(`/api/team-architect/teams/${teamId}/validate`, { method: 'POST' });
      if (!res.ok) throw new Error('Validation failed');
      const data = await res.json();
      toast.success(`Validation score: ${data.validation_score || 'N/A'}`);
      loadData();
      if (selectedTeam?.team_id === teamId) {
        const updated = await fetch(`/api/team-architect/teams/${teamId}`).then(r => r.json());
        setSelectedTeam(updated);
      }
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCloneTeam = async (teamId: string) => {
    const newName = prompt('Enter new team name:');
    if (!newName) return;
    try {
      const res = await fetch(`/api/team-architect/teams/${teamId}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
      });
      if (!res.ok) throw new Error('Clone failed');
      toast.success('Team cloned successfully');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleViewPattern = async (patternName: string) => {
    try {
      setPatternDetailLoading(true);
      const res = await fetch(`/api/team-architect/pattern/${encodeURIComponent(patternName)}`);
      if (!res.ok) throw new Error('Failed to load pattern');
      const data = await res.json();
      setSelectedPattern(data);
      setActiveSection('patterns');
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setPatternDetailLoading(false);
    }
  };

  const handleEvolve = async () => {
    if (!evolveForm.team_id || !evolveForm.changes.trim()) return;
    try {
      setEvolving(true);
      const res = await fetch('/api/team-architect/evolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: evolveForm.team_id,
          changes: evolveForm.changes,
          success_metrics: evolveForm.success_metrics || undefined,
          lessons_learned: evolveForm.lessons_learned || undefined,
          agent_adjustments: evolveForm.agent_adjustments || undefined,
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Evolution failed');
      toast.success('Evolution delta captured');
      setEvolveForm({ team_id: '', changes: '', success_metrics: '', lessons_learned: '', agent_adjustments: '' });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setEvolving(false);
    }
  };

  // ── Render Helpers ──

  const statusColors: Record<string, string> = {
    active: '#22c55e',
    draft: '#f59e0b',
    validated: '#3b82f6',
    archived: '#9ca3af',
    evolving: '#8b5cf6',
  };

  const statusLabels: Record<string, string> = {
    active: 'Active',
    draft: 'Draft',
    validated: 'Validated',
    archived: 'Archived',
    evolving: 'Evolving',
  };

  // ── Loading State ──

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Team Architect</h2>
          <p className="panel-subtitle">Design and generate agent team architectures</p>
        </div>
        <div className="panel-loading">
          <div className="spinner" />
          <span>Loading team architect data...</span>
        </div>
      </div>
    );
  }

  // ── Main Render ──

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Team Architect</h2>
        <p className="panel-subtitle">Design, generate, and evolve multi-agent team architectures for complex domains</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_teams}</span>
              <span className="stat-label">Total Teams</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_teams}</span>
              <span className="stat-label">Active</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.total_patterns}</span>
              <span className="stat-label">Patterns</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value">{stats.average_agent_count?.toFixed(1) || '0'}</span>
              <span className="stat-label">Avg Agents/Team</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.total_validations}</span>
              <span className="stat-label">Validations</span>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-content">
              <span className="stat-value" style={{ color: '#f59e0b' }}>{stats.total_evolutions}</span>
              <span className="stat-label">Evolutions</span>
            </div>
          </div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'generate', 'teams', 'patterns', 'evolve'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Overview Section ── */}
      {activeSection === 'overview' && (
        <div className="dashboard-section">
          {stats && (
            <>
              <h3>Pattern Usage Distribution</h3>
              {Object.entries(stats.patterns_used || {}).length > 0 ? (
                Object.entries(stats.patterns_used).map(([pattern, count]) => (
                  <div key={pattern} className="dashboard-stat-row">
                    <span style={{ color: PATTERN_COLORS[pattern] || '#666', fontWeight: 600 }}>
                      {pattern}
                    </span>
                    <strong>{count}</strong>
                  </div>
                ))
              ) : (
                <div className="panel-empty">No pattern usage data yet</div>
              )}

              <h3 style={{ marginTop: 20 }}>Recent Teams</h3>
              {teams.length === 0 ? (
                <div className="panel-empty">No teams created yet. Go to the Generate tab to create one.</div>
              ) : (
                <div className="forge-skill-list">
                  {teams.slice(0, 5).map(team => (
                    <div
                      key={team.team_id}
                      className="forge-skill-card"
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleViewTeam(team.team_id)}
                    >
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{team.team_name}</div>
                        <span
                          className="dashboard-badge"
                          style={{
                            background: PATTERN_COLORS[team.pattern] || '#666',
                            color: '#fff',
                          }}
                        >
                          {team.pattern}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>
                          Agents: {team.agent_count} | Complexity: {team.complexity} | Status:{' '}
                          <span style={{ color: statusColors[team.status] || '#666', fontWeight: 600 }}>
                            {statusLabels[team.status] || team.status}
                          </span>
                        </div>
                        {team.validation_score !== null && (
                          <div>
                            Validation Score:{' '}
                            <span style={{
                              color: (team.validation_score || 0) >= 0.7 ? '#22c55e' : (team.validation_score || 0) >= 0.4 ? '#f59e0b' : '#ef4444',
                              fontWeight: 600,
                            }}>
                              {((team.validation_score || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        )}
                        <div>Created: {new Date(team.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Generate Section ── */}
      {activeSection === 'generate' && (
        <div className="dashboard-section">
          <h3>Generate Team Architecture</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Domain Description</label>
              <textarea
                rows={4}
                value={generateForm.domain_description}
                onChange={e => setGenerateForm(f => ({ ...f, domain_description: e.target.value }))}
                placeholder="Describe the domain for which you need a team architecture, e.g., 'A multi-agent system for automated code review, testing, and deployment'"
              />
            </div>
            <div className="form-group">
              <label>Team Name</label>
              <input
                type="text"
                value={generateForm.team_name}
                onChange={e => setGenerateForm(f => ({ ...f, team_name: e.target.value }))}
                placeholder="My Team"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Preferred Pattern</label>
                <select
                  value={generateForm.preferred_pattern}
                  onChange={e => setGenerateForm(f => ({ ...f, preferred_pattern: e.target.value }))}
                >
                  <option value="">Auto-detect</option>
                  {PATTERN_NAMES.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Agent Count</label>
                <input
                  type="number"
                  min={2}
                  max={20}
                  value={generateForm.agent_count}
                  onChange={e => setGenerateForm(f => ({ ...f, agent_count: parseInt(e.target.value) || 4 }))}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Complexity</label>
                <select
                  value={generateForm.complexity}
                  onChange={e => setGenerateForm(f => ({ ...f, complexity: e.target.value }))}
                >
                  {COMPLEXITY_OPTIONS.map(c => (
                    <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Scale</label>
                <select
                  value={generateForm.scale}
                  onChange={e => setGenerateForm(f => ({ ...f, scale: e.target.value }))}
                >
                  {SCALE_OPTIONS.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn-primary"
                onClick={handleAnalyze}
                disabled={generating || !generateForm.domain_description.trim()}
                style={{ background: '#8b5cf6' }}
              >
                {generating ? 'Analyzing...' : 'Analyze Domain'}
              </button>
              <button
                className="btn-primary"
                onClick={handleGenerate}
                disabled={generating || !generateForm.domain_description.trim()}
              >
                {generating ? 'Generating...' : 'Generate Team'}
              </button>
            </div>
          </div>

          {/* Analysis Result */}
          {analyzeResult && (
            <div style={{
              marginTop: 20,
              padding: 16,
              background: '#f8fafc',
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}>
              <h4>Analysis Result</h4>
              <div style={{ marginTop: 8, fontSize: '0.9rem', color: '#475569' }}>
                {analyzeResult.recommended_pattern && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Recommended Pattern:</strong>{' '}
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      background: PATTERN_COLORS[analyzeResult.recommended_pattern] || '#666',
                      color: '#fff',
                      borderRadius: 4,
                      fontSize: '0.8rem',
                    }}>
                      {analyzeResult.recommended_pattern}
                    </span>
                  </div>
                )}
                {analyzeResult.suggested_agent_count && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Suggested Agents:</strong> {analyzeResult.suggested_agent_count}
                  </div>
                )}
                {analyzeResult.domain_complexity && (
                  <div style={{ marginBottom: 4 }}>
                    <strong>Domain Complexity:</strong> {analyzeResult.domain_complexity}
                  </div>
                )}
                {analyzeResult.reasoning && (
                  <div style={{ marginTop: 8, padding: 8, background: '#fff', borderRadius: 4, border: '1px solid #e2e8f0' }}>
                    <strong>Reasoning:</strong> {analyzeResult.reasoning}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Teams Section ── */}
      {activeSection === 'teams' && (
        <div className="dashboard-section">
          {selectedTeam ? (
            /* Team Detail View */
            teamDetailLoading ? (
              <div className="panel-loading">
                <div className="spinner" />
                <span>Loading team details...</span>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                  <div>
                    <h3>{selectedTeam.team_name}</h3>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                      <span className="dashboard-badge" style={{ background: PATTERN_COLORS[selectedTeam.pattern] || '#666', color: '#fff' }}>
                        {selectedTeam.pattern}
                      </span>
                      <span className="dashboard-badge" style={{ background: statusColors[selectedTeam.status] || '#9ca3af', color: '#fff' }}>
                        {statusLabels[selectedTeam.status] || selectedTeam.status}
                      </span>
                      {selectedTeam.validation_score !== null && (
                        <span className="dashboard-badge" style={{
                          background: (selectedTeam.validation_score || 0) >= 0.7 ? '#22c55e' : (selectedTeam.validation_score || 0) >= 0.4 ? '#f59e0b' : '#ef4444',
                          color: '#fff',
                        }}>
                          Score: {((selectedTeam.validation_score || 0) * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      className="btn-sm"
                      style={{ background: '#3b82f6', color: '#fff', border: 'none' }}
                      onClick={() => handleValidateTeam(selectedTeam.team_id)}
                    >
                      Validate
                    </button>
                    <button
                      className="btn-sm"
                      style={{ background: '#22c55e', color: '#fff', border: 'none' }}
                      onClick={() => handleCloneTeam(selectedTeam.team_id)}
                    >
                      Clone
                    </button>
                    <button
                      className="btn-sm"
                      style={{ background: '#9ca3af', color: '#fff', border: 'none' }}
                      onClick={() => setSelectedTeam(null)}
                    >
                      Back to List
                    </button>
                  </div>
                </div>

                {/* Domain Info */}
                <div style={{ marginBottom: 16, padding: 12, background: '#f8fafc', borderRadius: 8 }}>
                  <div style={{ fontSize: '0.9rem', color: '#475569' }}>
                    <strong>Domain:</strong> {selectedTeam.domain_description}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: 4 }}>
                    Complexity: {selectedTeam.complexity} | Agents: {selectedTeam.agent_count}
                  </div>
                </div>

                {/* Validation Issues */}
                {selectedTeam.validation_issues && selectedTeam.validation_issues.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <h4>Validation Issues</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {selectedTeam.validation_issues.map((issue, idx) => (
                        <div key={idx} style={{
                          padding: '8px 12px',
                          background: '#fffbeb',
                          border: '1px solid #fde68a',
                          borderRadius: 6,
                          fontSize: '0.85rem',
                          color: '#92400e',
                        }}>
                          {issue}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Team Members */}
                <h4>Team Members ({selectedTeam.members?.length || 0})</h4>
                {selectedTeam.members && selectedTeam.members.length > 0 ? (
                  <div className="forge-skill-list">
                    {selectedTeam.members.map((member, idx) => (
                      <div key={member.agent_id || idx} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{member.name || 'Unnamed Agent'}</div>
                          <span className="dashboard-badge" style={{ background: '#4f6ef7', color: '#fff' }}>
                            {member.role}
                          </span>
                        </div>
                        <div className="forge-skill-meta">
                          {member.responsibilities && member.responsibilities.length > 0 && (
                            <div>
                              <strong>Responsibilities:</strong>
                              <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                                {member.responsibilities.map((r, i) => (
                                  <li key={i} style={{ fontSize: '0.85rem', color: '#475569' }}>{r}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="panel-empty">No members defined</div>
                )}

                {/* Meta */}
                <div style={{ marginTop: 16, padding: 12, background: '#f9fafb', borderRadius: 8, fontSize: '0.85rem', color: '#6b7280' }}>
                  <div>Team ID: {selectedTeam.team_id}</div>
                  <div>Created: {new Date(selectedTeam.created_at).toLocaleString()}</div>
                  <div>Updated: {new Date(selectedTeam.updated_at).toLocaleString()}</div>
                </div>
              </>
            )
          ) : (
            /* Team List View */
            <>
              <h3>Generated Teams ({teams.length})</h3>
              {teams.length === 0 ? (
                <div className="panel-empty">No teams yet. Go to the Generate tab to create one.</div>
              ) : (
                <div className="forge-skill-list">
                  {teams.map(team => (
                    <div key={team.team_id} className="forge-skill-card">
                      <div className="forge-skill-header">
                        <div className="forge-skill-name">{team.team_name}</div>
                        <span
                          className="dashboard-badge"
                          style={{ background: PATTERN_COLORS[team.pattern] || '#666', color: '#fff' }}
                        >
                          {team.pattern}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>
                          Agents: {team.agent_count} | Complexity: {team.complexity} | Status:{' '}
                          <span style={{ color: statusColors[team.status] || '#666', fontWeight: 600 }}>
                            {statusLabels[team.status] || team.status}
                          </span>
                        </div>
                        {team.validation_score !== null && (
                          <div>
                            Validation Score:{' '}
                            <span style={{
                              color: (team.validation_score || 0) >= 0.7 ? '#22c55e' : (team.validation_score || 0) >= 0.4 ? '#f59e0b' : '#ef4444',
                              fontWeight: 600,
                            }}>
                              {((team.validation_score || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        )}
                        <div>Created: {new Date(team.created_at).toLocaleString()}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                        <button
                          className="btn-sm"
                          style={{ background: '#4f6ef7', color: '#fff', border: 'none' }}
                          onClick={() => handleViewTeam(team.team_id)}
                        >
                          View Details
                        </button>
                        <button
                          className="btn-sm"
                          style={{ background: '#3b82f6', color: '#fff', border: 'none' }}
                          onClick={() => handleValidateTeam(team.team_id)}
                        >
                          Validate
                        </button>
                        <button
                          className="btn-sm"
                          style={{ background: '#22c55e', color: '#fff', border: 'none' }}
                          onClick={() => handleCloneTeam(team.team_id)}
                        >
                          Clone
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Patterns Section ── */}
      {activeSection === 'patterns' && (
        <div className="dashboard-section">
          {selectedPattern ? (
            /* Pattern Detail View */
            patternDetailLoading ? (
              <div className="panel-loading">
                <div className="spinner" />
                <span>Loading pattern details...</span>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div>
                    <h3>{selectedPattern.name}</h3>
                    <span className="dashboard-badge" style={{
                      background: PATTERN_COLORS[selectedPattern.name] || '#666',
                      color: '#fff',
                      display: 'inline-block',
                      marginTop: 4,
                    }}>
                      {selectedPattern.category || 'General'}
                    </span>
                  </div>
                  <button
                    className="btn-sm"
                    style={{ background: '#9ca3af', color: '#fff', border: 'none' }}
                    onClick={() => setSelectedPattern(null)}
                  >
                    Back to List
                  </button>
                </div>

                <div style={{ marginBottom: 16, padding: 12, background: '#f8fafc', borderRadius: 8, fontSize: '0.9rem', color: '#475569' }}>
                  {selectedPattern.description}
                </div>

                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 16 }}>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value">{selectedPattern.agent_count}</span>
                      <span className="stat-label">Agents</span>
                    </div>
                  </div>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value" style={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>
                        {selectedPattern.complexity}
                      </span>
                      <span className="stat-label">Complexity</span>
                    </div>
                  </div>
                  <div className="stat-item" style={{ flex: '1 0 auto' }}>
                    <div className="stat-content">
                      <span className="stat-value" style={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>
                        {selectedPattern.scale}
                      </span>
                      <span className="stat-label">Scale</span>
                    </div>
                  </div>
                </div>

                {selectedPattern.use_cases && selectedPattern.use_cases.length > 0 && (
                  <div>
                    <h4>Use Cases</h4>
                    <ul style={{ margin: '8px 0 0 16px', padding: 0 }}>
                      {selectedPattern.use_cases.map((uc, idx) => (
                        <li key={idx} style={{ fontSize: '0.85rem', color: '#475569', marginBottom: 4 }}>{uc}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )
          ) : (
            /* Pattern List View */
            <>
              <h3>Available Team Patterns</h3>
              <p style={{ color: '#6b7280', fontSize: '0.9rem', marginBottom: 16 }}>
                Select a pattern to view detailed information about its structure, use cases, and recommended agent count.
              </p>
              {patterns.length === 0 ? (
                <div className="panel-empty">No patterns available</div>
              ) : (
                <div className="forge-skill-list">
                  {patterns.map(pattern => (
                    <div
                      key={pattern.name}
                      className="forge-skill-card"
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleViewPattern(pattern.name)}
                    >
                      <div className="forge-skill-header">
                        <div className="forge-skill-name" style={{ color: PATTERN_COLORS[pattern.name] || '#374151' }}>
                          {pattern.name}
                        </div>
                        <span className="dashboard-badge" style={{
                          background: PATTERN_COLORS[pattern.name] || '#666',
                          color: '#fff',
                        }}>
                          {pattern.category || 'General'}
                        </span>
                      </div>
                      <div className="forge-skill-meta">
                        <div>{pattern.description}</div>
                        <div style={{ marginTop: 4 }}>
                          Agents: {pattern.agent_count} | Complexity: {pattern.complexity} | Scale: {pattern.scale}
                        </div>
                        {pattern.use_cases && pattern.use_cases.length > 0 && (
                          <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {pattern.use_cases.slice(0, 3).map((uc, idx) => (
                              <span key={idx} style={{
                                padding: '2px 8px',
                                background: '#e8eaf6',
                                color: '#4f6ef7',
                                borderRadius: 12,
                                fontSize: '0.7rem',
                              }}>
                                {uc}
                              </span>
                            ))}
                            {pattern.use_cases.length > 3 && (
                              <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>
                                +{pattern.use_cases.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Evolve Section ── */}
      {activeSection === 'evolve' && (
        <div className="dashboard-section">
          <h3>Capture Evolution Delta</h3>
          <p style={{ color: '#6b7280', fontSize: '0.9rem', marginBottom: 16 }}>
            Record how a team architecture has evolved based on real-world execution feedback.
          </p>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Team</label>
              <select
                value={evolveForm.team_id}
                onChange={e => setEvolveForm(f => ({ ...f, team_id: e.target.value }))}
              >
                <option value="">Select a team...</option>
                {teams.map(t => (
                  <option key={t.team_id} value={t.team_id}>{t.team_name} ({t.pattern})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Changes Made</label>
              <textarea
                rows={3}
                value={evolveForm.changes}
                onChange={e => setEvolveForm(f => ({ ...f, changes: e.target.value }))}
                placeholder="Describe the changes made to the team architecture, e.g., 'Added a QA agent to the Pipeline pattern'"
              />
            </div>
            <div className="form-group">
              <label>Success Metrics</label>
              <textarea
                rows={2}
                value={evolveForm.success_metrics}
                onChange={e => setEvolveForm(f => ({ ...f, success_metrics: e.target.value }))}
                placeholder="Key metrics that improved after the change, e.g., 'Bug detection rate improved by 30%'"
              />
            </div>
            <div className="form-group">
              <label>Lessons Learned</label>
              <textarea
                rows={2}
                value={evolveForm.lessons_learned}
                onChange={e => setEvolveForm(f => ({ ...f, lessons_learned: e.target.value }))}
                placeholder="What was learned from this evolution, e.g., 'Fan-out patterns work best for independent sub-tasks'"
              />
            </div>
            <div className="form-group">
              <label>Agent Adjustments</label>
              <textarea
                rows={2}
                value={evolveForm.agent_adjustments}
                onChange={e => setEvolveForm(f => ({ ...f, agent_adjustments: e.target.value }))}
                placeholder="Specific agent role or responsibility adjustments made"
              />
            </div>
            <button
              className="btn-primary"
              onClick={handleEvolve}
              disabled={evolving || !evolveForm.team_id || !evolveForm.changes.trim()}
            >
              {evolving ? 'Capturing...' : 'Capture Evolution'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamArchitectPanel;