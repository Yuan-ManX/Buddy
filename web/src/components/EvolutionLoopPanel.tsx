import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

// Internal type definitions for the evolution loop data structures
interface EvolutionLoopStats {
  total_skills: number;
  active_skills: number;
  improvements: number;
  learning_events: number;
  user_models: number;
  pending_nudges: number;
}

interface EvolutionSkill {
  skill_id: string;
  name: string;
  description: string;
  category: string;
  status: string;
  triggers: string[];
  steps: string[];
  created_at: string;
  updated_at: string;
  usage_count?: number;
  success_rate?: number;
}

interface EvolutionEvent {
  event_id: string;
  trigger: string;
  session_id: string;
  agent_id: string;
  description: string;
  context: Record<string, unknown>;
  outcome: string;
  complexity_score: number;
  novel_patterns: string[];
  skills_used: string[];
  tokens_used: number;
  duration_ms: number;
  user_feedback: string;
  created_at: string;
}

interface EvolutionNudge {
  nudge_index: number;
  nudge_id: string;
  category: string;
  priority: string;
  message: string;
  suggested_action: string;
  status: string;
  created_at: string;
}

interface UserModelData {
  user_id: string;
  interaction_count: number;
  session_count: number;
  feedback_count: number;
  last_active: string;
  preferences: Record<string, unknown>;
  traits: Record<string, unknown>;
}

export const EvolutionLoopPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<EvolutionLoopStats | null>(null);
  const [skills, setSkills] = useState<EvolutionSkill[]>([]);
  const [nudges, setNudges] = useState<EvolutionNudge[]>([]);
  const [userModel, setUserModel] = useState<UserModelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'skills' | 'events' | 'nudges' | 'userModel'>('overview');

  // Skills filter state
  const [skillFilterCategory, setSkillFilterCategory] = useState('');
  const [skillFilterStatus, setSkillFilterStatus] = useState('');

  // Create skill form
  const [skillForm, setSkillForm] = useState({
    name: '',
    description: '',
    category: '',
    triggers: '',
    steps: '',
    status: 'active',
  });

  // Capture event form
  const [eventForm, setEventForm] = useState({
    trigger: '',
    session_id: '',
    agent_id: '',
    description: '',
    context: '',
    outcome: '',
    complexity_score: '',
    novel_patterns: '',
    skills_used: '',
    tokens_used: '',
    duration_ms: '',
    user_feedback: '',
  });

  // User model form
  const [userModelUserId, setUserModelUserId] = useState('');
  const [preferenceForm, setPreferenceForm] = useState({ key: '', value: '' });

  // Compress form
  const [compressMaxEvents, setCompressMaxEvents] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, n] = await Promise.all([
        api.evolutionLoop.stats(),
        api.evolutionLoop.nudges(),
      ]);
      setStats(s);
      setNudges(n.nudges || []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load evolution loop data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Load skills with filters
  const loadSkills = useCallback(async () => {
    try {
      const result = await api.evolutionLoop.skills({
        category: skillFilterCategory || undefined,
        status: skillFilterStatus || undefined,
      });
      setSkills(result.skills || []);
    } catch (e: any) {
      toast.error(e.message);
    }
  }, [skillFilterCategory, skillFilterStatus, toast]);

  useEffect(() => {
    if (activeSection === 'skills') {
      loadSkills();
    }
  }, [activeSection, loadSkills]);

  // Load user model
  const loadUserModel = useCallback(async () => {
    if (!userModelUserId.trim()) return;
    try {
      const result = await api.evolutionLoop.userModel(userModelUserId.trim());
      setUserModel(result);
    } catch (e: any) {
      toast.error(e.message);
    }
  }, [userModelUserId, toast]);

  const handleCreateSkill = async () => {
    if (!skillForm.name.trim()) return;
    try {
      await api.evolutionLoop.createSkill({
        name: skillForm.name.trim(),
        description: skillForm.description || undefined,
        category: skillForm.category || undefined,
        triggers: skillForm.triggers ? skillForm.triggers.split(',').map((s: string) => s.trim()) : undefined,
        steps: skillForm.steps ? skillForm.steps.split(',').map((s: string) => s.trim()) : undefined,
        status: skillForm.status || undefined,
      });
      toast.success(`Skill "${skillForm.name}" created successfully`);
      setSkillForm({ name: '', description: '', category: '', triggers: '', steps: '', status: 'active' });
      loadSkills();
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCaptureEvent = async () => {
    if (!eventForm.description.trim() && !eventForm.trigger.trim()) return;
    try {
      await api.evolutionLoop.createEvent({
        trigger: eventForm.trigger || undefined,
        session_id: eventForm.session_id || undefined,
        agent_id: eventForm.agent_id || undefined,
        description: eventForm.description || undefined,
        context: eventForm.context || undefined,
        outcome: eventForm.outcome || undefined,
        complexity_score: eventForm.complexity_score ? Number(eventForm.complexity_score) : undefined,
        novel_patterns: eventForm.novel_patterns ? eventForm.novel_patterns.split(',').map((s: string) => s.trim()) : undefined,
        skills_used: eventForm.skills_used ? eventForm.skills_used.split(',').map((s: string) => s.trim()) : undefined,
        tokens_used: eventForm.tokens_used ? Number(eventForm.tokens_used) : undefined,
        duration_ms: eventForm.duration_ms ? Number(eventForm.duration_ms) : undefined,
        user_feedback: eventForm.user_feedback || undefined,
      });
      toast.success('Learning event captured successfully');
      setEventForm({
        trigger: '', session_id: '', agent_id: '', description: '', context: '',
        outcome: '', complexity_score: '', novel_patterns: '', skills_used: '',
        tokens_used: '', duration_ms: '', user_feedback: '',
      });
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleProcessNudge = async (nudgeIndex: number, action: string) => {
    try {
      await api.evolutionLoop.processNudge({ nudge_index: nudgeIndex, action });
      toast.success(`Nudge ${action} successfully`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleSetPreference = async () => {
    if (!preferenceForm.key.trim()) return;
    try {
      await api.evolutionLoop.setPreference({
        key: preferenceForm.key.trim(),
        value: preferenceForm.value,
      });
      toast.success(`Preference "${preferenceForm.key}" updated`);
      setPreferenceForm({ key: '', value: '' });
      loadUserModel();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleCompress = async () => {
    if (!compressMaxEvents.trim()) return;
    try {
      const result = await api.evolutionLoop.compress({
        max_events: Number(compressMaxEvents),
      });
      toast.success(`Compression complete: ${result.compressed_count || 0} trajectories compressed`);
      setCompressMaxEvents('');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // Status and category color maps
  const statusColors: Record<string, string> = {
    active: '#22c55e',
    inactive: '#9ca3af',
    draft: '#f59e0b',
    deprecated: '#ef4444',
    learning: '#3b82f6',
  };

  const categoryColors: Record<string, string> = {
    reasoning: '#4f6ef7',
    tool_use: '#22c55e',
    memory: '#f59e0b',
    planning: '#8b5cf6',
    communication: '#ef4444',
    execution: '#06b6d4',
    analysis: '#ec4899',
    default: '#6b7280',
  };

  const nudgePriorityColors: Record<string, string> = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#22c55e',
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>Evolution Loop</h2>
          <p className="panel-subtitle">Continuous learning, skill evolution, and user model optimization</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading evolution loop data...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Evolution Loop</h2>
        <p className="panel-subtitle">Continuous learning, skill evolution, and user model optimization</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.total_skills}</span><span className="stat-label">Total Skills</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.active_skills}</span><span className="stat-label">Active Skills</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.improvements}</span><span className="stat-label">Improvements</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.learning_events}</span><span className="stat-label">Learning Events</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value">{stats.user_models}</span><span className="stat-label">User Models</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: stats.pending_nudges > 0 ? '#f59e0b' : undefined }}>{stats.pending_nudges}</span><span className="stat-label">Pending Nudges</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'skills', 'events', 'nudges', 'userModel'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s === 'userModel' ? 'User Model' : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Section */}
      {activeSection === 'overview' && stats && (
        <div className="dashboard-section">
          <h3>Evolution Loop Overview</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
            <div className="forge-skill-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#4f6ef7' }}>{stats.total_skills}</div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>Total Skills</div>
              <div style={{ fontSize: '0.8rem', color: '#22c55e', marginTop: 4 }}>{stats.active_skills} active</div>
            </div>
            <div className="forge-skill-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#8b5cf6' }}>{stats.learning_events}</div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>Learning Events</div>
            </div>
            <div className="forge-skill-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#22c55e' }}>{stats.improvements}</div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>Improvements Made</div>
            </div>
            <div className="forge-skill-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#f59e0b' }}>{stats.pending_nudges}</div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>Pending Nudges</div>
            </div>
          </div>

          {/* Trajectory Compression */}
          <h3 style={{ marginTop: 24 }}>Trajectory Compression</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Max Events to Compress</label>
              <input
                type="number"
                value={compressMaxEvents}
                onChange={e => setCompressMaxEvents(e.target.value)}
                placeholder="Enter maximum number of events to compress"
              />
            </div>
            <button className="btn-primary" onClick={handleCompress} disabled={!compressMaxEvents.trim()}>
              Compress Trajectories
            </button>
          </div>
        </div>
      )}

      {/* Skills Section */}
      {activeSection === 'skills' && (
        <div className="dashboard-section">
          <h3>Skills Management</h3>

          {/* Filters */}
          <div className="form-row" style={{ marginBottom: 16 }}>
            <div className="form-group">
              <label>Filter by Category</label>
              <select value={skillFilterCategory} onChange={e => setSkillFilterCategory(e.target.value)}>
                <option value="">All Categories</option>
                <option value="reasoning">Reasoning</option>
                <option value="tool_use">Tool Use</option>
                <option value="memory">Memory</option>
                <option value="planning">Planning</option>
                <option value="communication">Communication</option>
                <option value="execution">Execution</option>
                <option value="analysis">Analysis</option>
              </select>
            </div>
            <div className="form-group">
              <label>Filter by Status</label>
              <select value={skillFilterStatus} onChange={e => setSkillFilterStatus(e.target.value)}>
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="draft">Draft</option>
                <option value="deprecated">Deprecated</option>
                <option value="learning">Learning</option>
              </select>
            </div>
          </div>

          {/* Skills List */}
          {skills.length === 0 ? (
            <div className="panel-empty">No skills found. Create a new skill below.</div>
          ) : (
            <div className="forge-skill-list">
              {skills.map(skill => (
                <div key={skill.skill_id} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{skill.name}</div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span className="dashboard-badge" style={{
                        background: categoryColors[skill.category] || categoryColors.default,
                        color: '#fff',
                      }}>
                        {skill.category}
                      </span>
                      <span className="dashboard-badge" style={{
                        background: statusColors[skill.status] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {skill.status}
                      </span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    {skill.description && <div>{skill.description}</div>}
                    {skill.triggers.length > 0 && (
                      <div>Triggers: {skill.triggers.join(', ')}</div>
                    )}
                    {skill.steps.length > 0 && (
                      <div>Steps: {skill.steps.length} step{skill.steps.length !== 1 ? 's' : ''}</div>
                    )}
                    {skill.usage_count !== undefined && (
                      <div>Usage: {skill.usage_count} | Success Rate: {skill.success_rate !== undefined ? `${(skill.success_rate * 100).toFixed(0)}%` : 'N/A'}</div>
                    )}
                    <div>Created: {new Date(skill.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Create Skill Form */}
          <h3 style={{ marginTop: 24 }}>Create New Skill</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Skill Name *</label>
              <input
                type="text"
                value={skillForm.name}
                onChange={e => setSkillForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g., Code Review Assistant"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={skillForm.description}
                onChange={e => setSkillForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what this skill does"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Category</label>
                <select value={skillForm.category} onChange={e => setSkillForm(f => ({ ...f, category: e.target.value }))}>
                  <option value="">Select Category</option>
                  <option value="reasoning">Reasoning</option>
                  <option value="tool_use">Tool Use</option>
                  <option value="memory">Memory</option>
                  <option value="planning">Planning</option>
                  <option value="communication">Communication</option>
                  <option value="execution">Execution</option>
                  <option value="analysis">Analysis</option>
                </select>
              </div>
              <div className="form-group">
                <label>Status</label>
                <select value={skillForm.status} onChange={e => setSkillForm(f => ({ ...f, status: e.target.value }))}>
                  <option value="active">Active</option>
                  <option value="draft">Draft</option>
                  <option value="learning">Learning</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Triggers (comma-separated)</label>
              <input
                type="text"
                value={skillForm.triggers}
                onChange={e => setSkillForm(f => ({ ...f, triggers: e.target.value }))}
                placeholder="e.g., code_review_request, pull_request_opened"
              />
            </div>
            <div className="form-group">
              <label>Steps (comma-separated)</label>
              <input
                type="text"
                value={skillForm.steps}
                onChange={e => setSkillForm(f => ({ ...f, steps: e.target.value }))}
                placeholder="e.g., analyze_code, identify_patterns, suggest_improvements"
              />
            </div>
            <button className="btn-primary" onClick={handleCreateSkill} disabled={!skillForm.name.trim()}>
              Create Skill
            </button>
          </div>
        </div>
      )}

      {/* Events Section */}
      {activeSection === 'events' && (
        <div className="dashboard-section">
          <h3>Capture Learning Event</h3>
          <p style={{ color: '#6b7280', fontSize: '0.85rem', marginBottom: 16 }}>
            Record a learning event to help the system evolve and improve its skills over time.
          </p>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Trigger</label>
                <input
                  type="text"
                  value={eventForm.trigger}
                  onChange={e => setEventForm(f => ({ ...f, trigger: e.target.value }))}
                  placeholder="e.g., user_request, scheduled_task"
                />
              </div>
              <div className="form-group">
                <label>Session ID</label>
                <input
                  type="text"
                  value={eventForm.session_id}
                  onChange={e => setEventForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session identifier"
                />
              </div>
              <div className="form-group">
                <label>Agent ID</label>
                <input
                  type="text"
                  value={eventForm.agent_id}
                  onChange={e => setEventForm(f => ({ ...f, agent_id: e.target.value }))}
                  placeholder="Agent identifier"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={eventForm.description}
                onChange={e => setEventForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe what happened during this learning event"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Context</label>
                <textarea
                  rows={2}
                  value={eventForm.context}
                  onChange={e => setEventForm(f => ({ ...f, context: e.target.value }))}
                  placeholder="Additional context information"
                />
              </div>
              <div className="form-group">
                <label>Outcome</label>
                <textarea
                  rows={2}
                  value={eventForm.outcome}
                  onChange={e => setEventForm(f => ({ ...f, outcome: e.target.value }))}
                  placeholder="What was the result of this event?"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Complexity Score (0-1)</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={eventForm.complexity_score}
                  onChange={e => setEventForm(f => ({ ...f, complexity_score: e.target.value }))}
                  placeholder="0.0 - 1.0"
                />
              </div>
              <div className="form-group">
                <label>Tokens Used</label>
                <input
                  type="number"
                  value={eventForm.tokens_used}
                  onChange={e => setEventForm(f => ({ ...f, tokens_used: e.target.value }))}
                  placeholder="Total tokens consumed"
                />
              </div>
              <div className="form-group">
                <label>Duration (ms)</label>
                <input
                  type="number"
                  value={eventForm.duration_ms}
                  onChange={e => setEventForm(f => ({ ...f, duration_ms: e.target.value }))}
                  placeholder="Duration in milliseconds"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Novel Patterns (comma-separated)</label>
              <input
                type="text"
                value={eventForm.novel_patterns}
                onChange={e => setEventForm(f => ({ ...f, novel_patterns: e.target.value }))}
                placeholder="e.g., recursive_decomposition, parallel_batching"
              />
            </div>
            <div className="form-group">
              <label>Skills Used (comma-separated)</label>
              <input
                type="text"
                value={eventForm.skills_used}
                onChange={e => setEventForm(f => ({ ...f, skills_used: e.target.value }))}
                placeholder="e.g., code_review, refactoring, testing"
              />
            </div>
            <div className="form-group">
              <label>User Feedback</label>
              <textarea
                rows={2}
                value={eventForm.user_feedback}
                onChange={e => setEventForm(f => ({ ...f, user_feedback: e.target.value }))}
                placeholder="Any feedback from the user about this event"
              />
            </div>
            <button className="btn-primary" onClick={handleCaptureEvent}>
              Capture Learning Event
            </button>
          </div>
        </div>
      )}

      {/* Nudges Section */}
      {activeSection === 'nudges' && (
        <div className="dashboard-section">
          <h3>Pending Nudges ({nudges.length})</h3>
          {nudges.length === 0 ? (
            <div className="panel-empty">No pending nudges. The system is up to date.</div>
          ) : (
            <div className="forge-skill-list">
              {nudges.map((nudge, idx) => (
                <div key={nudge.nudge_id || idx} className="forge-skill-card">
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{nudge.message}</div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span className="dashboard-badge" style={{
                        background: nudgePriorityColors[nudge.priority] || '#9ca3af',
                        color: '#fff',
                      }}>
                        {nudge.priority}
                      </span>
                      <span className="dashboard-badge" style={{
                        background: '#e8eaf6',
                        color: '#4f6ef7',
                      }}>
                        {nudge.category}
                      </span>
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Suggested Action: {nudge.suggested_action}</div>
                    <div>Status: {nudge.status}</div>
                    <div>Created: {new Date(nudge.created_at).toLocaleString()}</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button
                      className="btn-sm"
                      style={{ background: '#22c55e', color: '#fff', border: 'none' }}
                      onClick={() => handleProcessNudge(nudge.nudge_index, 'apply')}
                    >
                      Apply
                    </button>
                    <button
                      className="btn-sm"
                      style={{ background: '#ef4444', color: '#fff', border: 'none' }}
                      onClick={() => handleProcessNudge(nudge.nudge_index, 'dismiss')}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* User Model Section */}
      {activeSection === 'userModel' && (
        <div className="dashboard-section">
          <h3>User Model</h3>

          {/* Load User Model */}
          <div className="form-row" style={{ marginBottom: 16 }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>User ID</label>
              <input
                type="text"
                value={userModelUserId}
                onChange={e => setUserModelUserId(e.target.value)}
                placeholder="Enter user ID to load model"
              />
            </div>
            <div className="form-group" style={{ alignSelf: 'flex-end' }}>
              <button className="btn-primary" onClick={loadUserModel} disabled={!userModelUserId.trim()}>
                Load User Model
              </button>
            </div>
          </div>

          {/* User Model Data */}
          {userModel ? (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginBottom: 20 }}>
                <div className="forge-skill-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#4f6ef7' }}>{userModel.interaction_count}</div>
                  <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>Interactions</div>
                </div>
                <div className="forge-skill-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#22c55e' }}>{userModel.session_count}</div>
                  <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>Sessions</div>
                </div>
                <div className="forge-skill-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#8b5cf6' }}>{userModel.feedback_count}</div>
                  <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>Feedback</div>
                </div>
                <div className="forge-skill-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f59e0b' }}>
                    {userModel.last_active ? new Date(userModel.last_active).toLocaleString() : 'N/A'}
                  </div>
                  <div style={{ color: '#6b7280', fontSize: '0.8rem' }}>Last Active</div>
                </div>
              </div>

              {/* Preferences */}
              {userModel.preferences && Object.keys(userModel.preferences).length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <h4>Preferences</h4>
                  <div className="forge-skill-list">
                    {Object.entries(userModel.preferences).map(([key, value]) => (
                      <div key={key} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{key}</div>
                        </div>
                        <div className="forge-skill-meta">
                          <div>{JSON.stringify(value)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Traits */}
              {userModel.traits && Object.keys(userModel.traits).length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <h4>Traits</h4>
                  <div className="forge-skill-list">
                    {Object.entries(userModel.traits).map(([key, value]) => (
                      <div key={key} className="forge-skill-card">
                        <div className="forge-skill-header">
                          <div className="forge-skill-name">{key}</div>
                        </div>
                        <div className="forge-skill-meta">
                          <div>{JSON.stringify(value)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Set Preference */}
              <h4 style={{ marginTop: 20 }}>Set Preference</h4>
              <div className="skill-execute" style={{ position: 'static' }}>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Key</label>
                    <input
                      type="text"
                      value={preferenceForm.key}
                      onChange={e => setPreferenceForm(f => ({ ...f, key: e.target.value }))}
                      placeholder="Preference key"
                    />
                  </div>
                  <div className="form-group" style={{ flex: 2 }}>
                    <label>Value</label>
                    <input
                      type="text"
                      value={preferenceForm.value}
                      onChange={e => setPreferenceForm(f => ({ ...f, value: e.target.value }))}
                      placeholder="Preference value"
                    />
                  </div>
                </div>
                <button
                  className="btn-primary"
                  onClick={handleSetPreference}
                  disabled={!preferenceForm.key.trim()}
                >
                  Set Preference
                </button>
              </div>
            </>
          ) : (
            <div className="panel-empty">Enter a user ID and click "Load User Model" to view user data.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default EvolutionLoopPanel;