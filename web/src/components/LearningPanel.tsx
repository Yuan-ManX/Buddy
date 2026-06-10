import React, { useState, useEffect } from 'react';
import type { Agent } from '../types';
import { api } from '../api/client';

interface LearningPanelProps {
  agent: Agent;
}

export const LearningPanel: React.FC<LearningPanelProps> = ({ agent }) => {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [patterns, setPatterns] = useState<Record<string, unknown>[]>([]);
  const [candidates, setCandidates] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cycleResult, setCycleResult] = useState<Record<string, unknown> | null>(null);
  const [running, setRunning] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, p, c] = await Promise.all([
        api.learning.stats(agent.id),
        api.learning.patterns(agent.id),
        api.learning.candidates(agent.id),
      ]);
      setStats(s as unknown as Record<string, unknown>);
      setPatterns(p as unknown as Record<string, unknown>[]);
      setCandidates(c as unknown as Record<string, unknown>[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load learning data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [agent.id]);

  const handleRunCycle = async () => {
    setRunning(true);
    setCycleResult(null);
    try {
      const result = await api.learning.runCycle(agent.id);
      setCycleResult(result as unknown as Record<string, unknown>);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run learning cycle');
    } finally {
      setRunning(false);
    }
  };

  const statusColors: Record<string, string> = {
    candidate: '#f59e0b',
    validated: '#3b82f6',
    promoted: '#10b981',
    rejected: '#ef4444',
    deprecated: '#94a3b8',
  };

  const patternTypeIcons: Record<string, string> = {
    workflow: '\u{1F504}',
    decision: '\u{1F9E0}',
    strategy: '\u{1F3AF}',
    conversation: '\u{1F4AC}',
    problem_solving: '\u{1F527}',
  };

  if (loading) {
    return <div className="panel-container"><div className="panel-loading">Loading learning data...</div></div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Learning Loop</h2>
          <div className="panel-subtitle">Autonomous skill discovery from interaction patterns</div>
        </div>
        <div className="panel-header-actions">
          <button
            className="btn-primary"
            onClick={handleRunCycle}
            disabled={running}
          >
            {running ? 'Running...' : 'Run Learning Cycle'}
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {cycleResult && (
        <div className="subagent-aggregated" style={{ marginBottom: '16px' }}>
          <div className="subagent-aggregated-header">CYCLE COMPLETE</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', marginTop: '8px' }}>
            {[
              { label: 'Patterns Found', value: (cycleResult.patterns_detected as number) ?? 0 },
              { label: 'Candidates', value: (cycleResult.candidates_generated as number) ?? 0 },
              { label: 'Skills Promoted', value: (cycleResult.skills_promoted as number) ?? 0 },
              { label: 'Cycle Duration', value: `${((cycleResult.cycle_duration_ms as number) ?? 0)}ms` as unknown as number },
            ].map(m => (
              <div key={m.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--blue)' }}>{String(m.value)}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{m.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="memory-stats-grid">
          <div className="memory-stat-card">
            <div className="memory-stat-value">{String(stats.total_interactions ?? 0)}</div>
            <div className="memory-stat-label">Total Interactions</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{String(stats.detected_patterns ?? 0)}</div>
            <div className="memory-stat-label">Patterns Detected</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{String(stats.generated_candidates ?? 0)}</div>
            <div className="memory-stat-label">Candidate Skills</div>
          </div>
          <div className="memory-stat-card">
            <div className="memory-stat-value">{String(stats.promoted_skills ?? 0)}</div>
            <div className="memory-stat-label">Promoted Skills</div>
          </div>
        </div>
      )}

      {/* Patterns */}
      <div className="dashboard-section">
        <h3>Detected Patterns ({patterns.length})</h3>
        {patterns.length === 0 ? (
          <div className="panel-empty">No patterns detected yet. Run a learning cycle when interactions accumulate.</div>
        ) : (
          <div className="subagent-tasks">
            {patterns.map((pattern, idx) => (
              <div key={(pattern.pattern_id as string) || idx} className="skill-card" style={{ cursor: 'default' }}>
                <div className="skill-card-icon">{patternTypeIcons[(pattern.pattern_type as string) || ''] || '\u{1F50D}'}</div>
                <div className="skill-card-info">
                  <div className="skill-card-name">{pattern.name as string || 'Unknown Pattern'}</div>
                  <div className="skill-card-desc">{pattern.description as string || ''}</div>
                  <div className="skill-card-cat" style={{ marginTop: '4px' }}>
                    {pattern.pattern_type as string} · {pattern.typical_actions ? (pattern.typical_actions as string[]).length : 0} actions · {pattern.frequency as number ?? 0} uses
                  </div>
                </div>
                <div className="memory-importance">
                  <div className="memory-importance-bar">
                    <div
                      className="memory-importance-fill"
                      style={{ width: `${((pattern.success_rate as number) ?? 0) * 100}%`, background: ((pattern.success_rate as number) ?? 0) > 0.7 ? '#10b981' : '#f59e0b' }}
                    />
                  </div>
                  <span>{(((pattern.success_rate as number) ?? 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Candidate Skills */}
      <div className="dashboard-section">
        <h3>Candidate Skills ({candidates.length})</h3>
        {candidates.length === 0 ? (
          <div className="panel-empty">No candidate skills generated yet.</div>
        ) : (
          <div className="subagent-tasks">
            {candidates.map((skill, idx) => {
              const status = (skill.status as string) || 'candidate';
              const confidence = (skill.confidence as number) ?? 0;
              return (
                <div key={(skill.candidate_id as string) || idx} className="task-card" style={{ borderColor: `${statusColors[status] || '#666'}33` }}>
                  <div className="task-card-header">
                    <span className="task-card-status" style={{ background: statusColors[status] || '#666' }}>
                      {status}
                    </span>
                    <span className="task-card-kind">{skill.name as string}</span>
                    <div className="memory-importance" style={{ marginLeft: 'auto' }}>
                      <div className="memory-importance-bar">
                        <div
                          className="memory-importance-fill"
                          style={{ width: `${confidence * 100}%` }}
                        />
                      </div>
                      <span>{(confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div className="task-card-title">{skill.description as string}</div>
                  <div className="task-card-time">
                    Source patterns: {((skill.source_patterns as string[]) || []).length}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};