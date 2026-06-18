import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { LearningLoopStatus, LearningNudge, LearningPattern, LearningSkill } from '../types';

export const LearningLoopPanel: React.FC = () => {
  const toast = useToast();
  const [status, setStatus] = useState<LearningLoopStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'observations' | 'patterns' | 'skills' | 'nudges' | 'evolve'>('overview');

  const [nudges, setNudges] = useState<LearningNudge[]>([]);
  const [patterns, setPatterns] = useState<LearningPattern[]>([]);
  const [skills, setSkills] = useState<LearningSkill[]>([]);
  const [agentId, setAgentId] = useState('');
  const [evolveResult, setEvolveResult] = useState<Record<string, unknown> | null>(null);

  const [observeForm, setObserveForm] = useState({
    observation_type: 'chat_message',
    agent_id: '',
    outcome: 'success',
    content: '',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, n, p, sk] = await Promise.all([
        api.learningLoop.status(),
        api.learningLoop.nudges(),
        api.learningLoop.patterns(),
        api.learningLoop.skills(),
      ]);
      setStatus(s);
      setNudges(n.nudges);
      setPatterns(p.patterns);
      setSkills(sk.skills);
    } catch (e: any) {
      setError(e.message || 'Failed to load learning data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleObserve = async () => {
    if (!observeForm.agent_id) return;
    try {
      let content: Record<string, unknown> = {};
      if (observeForm.content) {
        try { content = JSON.parse(observeForm.content); } catch { content = { text: observeForm.content }; }
      }
      await api.learningLoop.observe({
        observation_type: observeForm.observation_type,
        agent_id: observeForm.agent_id,
        content,
        outcome: observeForm.outcome,
      });
      setObserveForm({ observation_type: 'chat_message', agent_id: '', outcome: 'success', content: '' });
      toast.success('Observation recorded');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to record observation');
    }
  };

  const handleExtract = async () => {
    if (!agentId && !status) return;
    try {
      const result = await api.learningLoop.extract(agentId || undefined);
      setPatterns(result.patterns);
      toast.success(`Extracted ${result.total} patterns`);
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to extract patterns');
    }
  };

  const handleCompound = async () => {
    if (!agentId) return;
    try {
      const result = await api.learningLoop.compound(agentId);
      if ('error' in result) {
        toast.error(result.error);
      } else {
        toast.success(`Skill compounded: ${result.name}`);
        loadData();
      }
    } catch (e: any) {
      toast.error(e.message || 'Failed to compound skills');
    }
  };

  const handleEvolve = async () => {
    if (!agentId) return;
    try {
      const result = await api.learningLoop.evolve(agentId);
      setEvolveResult(result);
      toast.success('Agent evolved');
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to evolve agent');
    }
  };

  const handleRunCycle = async () => {
    if (!agentId) return;
    try {
      const result = await api.learningLoop.runCycle(agentId);
      toast.success(`Cycle complete: ${(result as any).patterns_extracted || 0} patterns extracted`);
      loadData();
    } catch (e: any) {
      toast.error(e.message || 'Failed to run cycle');
    }
  };

  const handleDismissNudge = async (nudgeId: string) => {
    try {
      await api.learningLoop.dismissNudge(nudgeId);
      setNudges(prev => prev.filter(n => n.nudge_id !== nudgeId));
      toast.success('Nudge dismissed');
    } catch (e: any) {
      toast.error(e.message || 'Failed to dismiss nudge');
    }
  };

  const handleActOnNudge = async (nudgeId: string) => {
    try {
      await api.learningLoop.actOnNudge(nudgeId);
      setNudges(prev => prev.filter(n => n.nudge_id !== nudgeId));
      toast.success('Nudge acted upon');
    } catch (e: any) {
      toast.error(e.message || 'Failed to act on nudge');
    }
  };

  if (loading && !status) {
    return (
      <div className="panel-container">
        <div className="panel-header"><h2>Learning Loop</h2></div>
        <div className="panel-loading">Loading learning data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-container">
        <div className="panel-header"><h2>Learning Loop</h2></div>
        <div className="panel-error">
          <p>{error}</p>
          <button className="btn-secondary" onClick={loadData}>Retry</button>
        </div>
      </div>
    );
  }

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'critical': return '#dc2626';
      case 'high': return '#f97316';
      case 'medium': return '#f59e0b';
      case 'low': return '#3b82f6';
      case 'suggestion': return '#6b7280';
      default: return '#9ca3af';
    }
  };

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Learning Loop</h2>
        <div className="panel-header-actions">
          <button className="btn-secondary btn-sm" onClick={loadData}>Refresh</button>
        </div>
      </div>

      {/* Section Navigation */}
      <div className="panel-tabs">
        {(['overview', 'observations', 'patterns', 'skills', 'nudges', 'evolve'] as const).map(section => (
          <button
            key={section}
            className={`panel-tab ${activeSection === section ? 'active' : ''}`}
            onClick={() => setActiveSection(section)}
          >
            {section === 'overview' && 'Overview'}
            {section === 'observations' && 'Observe'}
            {section === 'patterns' && 'Patterns'}
            {section === 'skills' && 'Skills'}
            {section === 'nudges' && 'Nudges'}
            {section === 'evolve' && 'Evolve'}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && status && (
        <div className="learning-overview">
          <div className="mesh-stats-grid">
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.observation.total_observations}</div>
              <div className="mesh-stat-label">Observations</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.extraction.total_patterns}</div>
              <div className="mesh-stat-label">Patterns</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.compounding.total_skills}</div>
              <div className="mesh-stat-label">Skills</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.evolution.total_evolutions}</div>
              <div className="mesh-stat-label">Evolutions</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.nudge.active_nudges}</div>
              <div className="mesh-stat-label">Active Nudges</div>
            </div>
            <div className="mesh-stat-card">
              <div className="mesh-stat-value">{status.user_model.interaction_count}</div>
              <div className="mesh-stat-label">Interactions</div>
            </div>
          </div>

          <div className="learning-agent-input">
            <h3>Agent ID for Operations</h3>
            <div className="form-row">
              <input
                type="text"
                value={agentId}
                onChange={e => setAgentId(e.target.value)}
                placeholder="Enter agent ID..."
                className="form-input"
              />
              <button className="btn-primary btn-sm" onClick={handleRunCycle}>Run Full Cycle</button>
              <button className="btn-secondary btn-sm" onClick={handleExtract}>Extract</button>
              <button className="btn-secondary btn-sm" onClick={handleCompound}>Compound</button>
              <button className="btn-secondary btn-sm" onClick={handleEvolve}>Evolve</button>
            </div>
          </div>
        </div>
      )}

      {/* Observations */}
      {activeSection === 'observations' && (
        <div className="learning-section">
          <h3>Record Observation</h3>
          <div className="delegate-form">
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                value={observeForm.agent_id}
                onChange={e => setObserveForm(f => ({ ...f, agent_id: e.target.value }))}
                placeholder="agent-id"
              />
            </div>
            <div className="form-group">
              <label>Observation Type</label>
              <select
                value={observeForm.observation_type}
                onChange={e => setObserveForm(f => ({ ...f, observation_type: e.target.value }))}
              >
                <option value="chat_message">Chat Message</option>
                <option value="tool_execution">Tool Execution</option>
                <option value="task_completion">Task Completion</option>
                <option value="user_feedback">User Feedback</option>
                <option value="error_occurred">Error Occurred</option>
                <option value="skill_created">Skill Created</option>
                <option value="skill_used">Skill Used</option>
              </select>
            </div>
            <div className="form-group">
              <label>Outcome</label>
              <select
                value={observeForm.outcome}
                onChange={e => setObserveForm(f => ({ ...f, outcome: e.target.value }))}
              >
                <option value="success">Success</option>
                <option value="partial">Partial</option>
                <option value="failure">Failure</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
            <div className="form-group">
              <label>Content (JSON or text)</label>
              <textarea
                value={observeForm.content}
                onChange={e => setObserveForm(f => ({ ...f, content: e.target.value }))}
                placeholder='{"tool_name": "read_file", "file_path": "..."}'
                rows={3}
              />
            </div>
            <button className="btn-primary" onClick={handleObserve}>Record Observation</button>
          </div>

          {status && (
            <div className="mesh-stats-grid" style={{ marginTop: '1rem' }}>
              {Object.entries(status.observation.by_type).map(([type, count]) => (
                <div key={type} className="mesh-stat-card">
                  <div className="mesh-stat-value">{count}</div>
                  <div className="mesh-stat-label">{type}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Patterns */}
      {activeSection === 'patterns' && (
        <div className="learning-section">
          <h3>Extracted Patterns ({patterns.length})</h3>
          {patterns.length === 0 ? (
            <div className="mesh-empty">No patterns extracted yet. Record observations and run extraction.</div>
          ) : (
            <div className="mesh-task-list">
              {patterns.map(pattern => (
                <div key={pattern.pattern_id} className="mesh-task-item">
                  <div className="mesh-task-title">{pattern.description}</div>
                  <div className="mesh-task-meta">
                    <span className="mesh-task-priority" style={{ backgroundColor: pattern.confidence >= 0.6 ? '#22c55e' : '#f59e0b' }}>
                      confidence: {(pattern.confidence * 100).toFixed(0)}%
                    </span>
                    <span className="mesh-task-target">frequency: {pattern.frequency}</span>
                    <span className="mesh-task-time">{pattern.pattern_type}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Skills */}
      {activeSection === 'skills' && (
        <div className="learning-section">
          <h3>Compound Skills ({skills.length})</h3>
          {skills.length === 0 ? (
            <div className="mesh-empty">No skills compounded yet. Extract patterns and run compounding.</div>
          ) : (
            <div className="mesh-task-list">
              {skills.map(skill => (
                <div key={skill.skill_id} className="mesh-task-item">
                  <div className="mesh-task-title">{skill.name}</div>
                  <div className="mesh-task-meta">
                    <span className="mesh-task-priority" style={{ backgroundColor: skill.confidence >= 0.6 ? '#22c55e' : '#f59e0b' }}>
                      confidence: {(skill.confidence * 100).toFixed(0)}%
                    </span>
                    <span className="mesh-task-target">used: {skill.usage_count}x</span>
                    <span className="mesh-task-time">source: {skill.skill_source}</span>
                  </div>
                  <div className="mesh-node-capabilities">
                    {skill.tools_required.map(tool => (
                      <span key={tool} className="mesh-cap-tag">{tool}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Nudges */}
      {activeSection === 'nudges' && (
        <div className="learning-section">
          <h3>Active Nudges ({nudges.length})</h3>
          {nudges.length === 0 ? (
            <div className="mesh-empty">No active nudges. Record more interactions to generate suggestions.</div>
          ) : (
            <div className="mesh-task-list">
              {nudges.map(nudge => (
                <div key={nudge.nudge_id} className="mesh-task-item" style={{ borderLeftColor: getPriorityColor(nudge.priority) }}>
                  <div className="mesh-task-title">{nudge.message}</div>
                  <div className="mesh-task-meta">
                    <span className="mesh-task-priority" style={{ backgroundColor: getPriorityColor(nudge.priority) }}>
                      {nudge.priority}
                    </span>
                    <span className="mesh-task-target">{nudge.category}</span>
                    <span className="mesh-task-time">{new Date(nudge.created_at).toLocaleString()}</span>
                  </div>
                  <div className="mesh-node-actions">
                    <button className="btn-primary btn-sm" onClick={() => handleActOnNudge(nudge.nudge_id)}>Act</button>
                    <button className="btn-secondary btn-sm" onClick={() => handleDismissNudge(nudge.nudge_id)}>Dismiss</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Evolve */}
      {activeSection === 'evolve' && (
        <div className="learning-section">
          <h3>Agent Evolution</h3>
          <div className="delegate-form">
            <div className="form-group">
              <label>Agent ID to Evolve</label>
              <input
                type="text"
                value={agentId}
                onChange={e => setAgentId(e.target.value)}
                placeholder="agent-id-to-evolve"
              />
            </div>
            <button className="btn-primary" onClick={handleEvolve}>Evolve Agent</button>
          </div>

          {evolveResult && (
            <div className="mesh-task-list" style={{ marginTop: '1rem' }}>
              <div className="mesh-task-item">
                <div className="mesh-task-title">Evolution Result</div>
                <pre style={{ fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(evolveResult, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {status && (
            <div className="mesh-stats-grid" style={{ marginTop: '1rem' }}>
              <div className="mesh-stat-card">
                <div className="mesh-stat-value">{status.evolution.total_evolutions}</div>
                <div className="mesh-stat-label">Total Evolutions</div>
              </div>
              <div className="mesh-stat-card">
                <div className="mesh-stat-value">{status.evolution.agents_evolved}</div>
                <div className="mesh-stat-label">Agents Evolved</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};