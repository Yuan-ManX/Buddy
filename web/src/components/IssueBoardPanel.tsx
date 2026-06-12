import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

const STATE_COLORS: Record<string, string> = {
  backlog: '#9ca3af',
  todo: '#3b82f6',
  in_progress: '#f59e0b',
  in_review: '#8b5cf6',
  done: '#10b981',
  cancelled: '#ef4444',
};

const STATE_EMOJIS: Record<string, string> = {
  backlog: '📋',
  todo: '✅',
  in_progress: '🚀',
  in_review: '👀',
  done: '🎉',
  cancelled: '❌',
};

const STATE_NAMES: Record<string, string> = {
  backlog: 'Backlog',
  todo: 'To Do',
  in_progress: 'In Progress',
  in_review: 'In Review',
  done: 'Done',
  cancelled: 'Cancelled',
};

const PRIORITY_COLORS: Record<string, string> = {
  low: '#9ca3af',
  medium: '#f59e0b',
  high: '#ef4444',
  urgent: '#dc2626',
};

const PRIORITY_EMOJIS: Record<string, string> = {
  low: '🔵',
  medium: '🟡',
  high: '🟠',
  urgent: '🔴',
};

interface Issue {
  id: string;
  title: string;
  description?: string;
  state: string;
  priority: string;
  tags: string[];
  agent_id?: string;
  agent_name?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

interface BoardStats {
  total_issues: number;
  by_state: Record<string, number>;
  by_priority: Record<string, number>;
}

interface AutopilotRule {
  id: string;
  name: string;
  agent_id: string;
  max_concurrent: number;
}

export const IssueBoardPanel: React.FC = () => {
  const [columns, setColumns] = useState<Record<string, Issue[]>>({});
  const [stats, setStats] = useState<BoardStats | null>(null);
  const [autopilotRules, setAutopilotRules] = useState<AutopilotRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showAutopilot, setShowAutopilot] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [stateFilter, setStateFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const { success: showSuccess, error: showError } = useToast();

  const [newIssue, setNewIssue] = useState({
    title: '',
    description: '',
    priority: 'medium',
    tags: [] as string[],
    agent_id: '',
  });

  const [newAutopilot, setNewAutopilot] = useState({
    name: '',
    agent_id: '',
    max_concurrent: 3,
  });

  useEffect(() => {
    loadBoard();
    loadStats();
    loadAutopilot();
  }, [stateFilter, priorityFilter]);

  const loadBoard = async () => {
    try {
      setLoading(true);
      const res = await api.board.listIssues({
        state: stateFilter || undefined,
        priority: priorityFilter || undefined,
      });
      // Group by state
      const grouped: Record<string, Issue[]> = {
        backlog: [],
        todo: [],
        in_progress: [],
        in_review: [],
        done: [],
        cancelled: [],
      };
      res.issues.forEach((issue: any) => grouped[issue.state].push(issue as Issue));
      setColumns(grouped);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load issue board');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const res = await api.board.stats();
      setStats(res as unknown as BoardStats);
    } catch (e) {
      console.error('Failed to load stats', e);
    }
  };

  const loadAutopilot = async () => {
    try {
      const res = await api.board.listAutopilot();
      setAutopilotRules(res.rules as unknown as AutopilotRule[]);
    } catch (e) {
      console.error('Failed to load autopilot rules', e);
    }
  };

  const handleCreate = async () => {
    if (!newIssue.title.trim()) return;
    try {
      await api.board.createIssue({
        ...newIssue,
        tags: newIssue.tags.filter(t => t.trim()),
      });
      setShowCreate(false);
      setNewIssue({ title: '', description: '', priority: 'medium', tags: [], agent_id: '' });
      loadBoard();
      loadStats();
      showSuccess('Issue created successfully');
    } catch (e: any) {
      setError(e.message);
      showError('Failed to create issue');
    }
  };

  const handleCreateAutopilot = async () => {
    if (!newAutopilot.name.trim() || !newAutopilot.agent_id.trim()) return;
    try {
      await api.board.createAutopilot(newAutopilot);
      setShowAutopilot(false);
      setNewAutopilot({ name: '', agent_id: '', max_concurrent: 3 });
      loadAutopilot();
      showSuccess('Autopilot rule created');
    } catch (e: any) {
      showError('Failed to create autopilot rule');
    }
  };

  const handleMoveIssue = async (issue: Issue, newState: string) => {
    try {
      await api.board.moveIssue(issue.id, newState);
      loadBoard();
      loadStats();
      showSuccess(`Moved "${issue.title}" to ${STATE_NAMES[newState]}`);
    } catch (e: any) {
      showError('Failed to move issue');
    }
  };

  const handleAssignIssue = async (issue: Issue, agentId: string) => {
    try {
      await api.board.assignIssue(issue.id, agentId);
      loadBoard();
      showSuccess(`Assigned "${issue.title}" to agent ${agentId}`);
    } catch (e: any) {
      showError('Failed to assign issue');
    }
  };

  const handleClaimIssue = async (issue: Issue, agentId: string) => {
    try {
      await api.board.claimIssue(issue.id, agentId);
      loadBoard();
      showSuccess(`Claimed "${issue.title}"`);
    } catch (e: any) {
      showError('Failed to claim issue');
    }
  };

  const handleCompleteIssue = async (issue: Issue) => {
    try {
      await api.board.completeIssue(issue.id);
      loadBoard();
      loadStats();
      showSuccess(`Completed "${issue.title}"`);
    } catch (e: any) {
      showError('Failed to complete issue');
    }
  };

  const handleDeleteIssue = async (issueId: string) => {
    if (!confirm('Are you sure you want to delete this issue?')) return;
    try {
      await api.board.deleteIssue(issueId);
      loadBoard();
      loadStats();
      showSuccess('Issue deleted');
    } catch (e: any) {
      showError('Failed to delete issue');
    }
  };

  const handleDeleteAutopilot = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this autopilot rule?')) return;
    try {
      await api.board.deleteAutopilot(ruleId);
      loadAutopilot();
      showSuccess('Autopilot rule deleted');
    } catch (e: any) {
      showError('Failed to delete autopilot rule');
    }
  };

  if (loading && !Object.keys(columns).length) {
    return <div className="panel-loading">Loading issue board...</div>;
  }

  return (
    <div className="panel-container">
      <div className="panel-header">
        <h2>Issue Board</h2>
        <div className="panel-header-actions">
          <button className="btn-secondary" onClick={() => setShowAutopilot(true)}>
            ⚙️ Autopilot
          </button>
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + New Issue
          </button>
        </div>
      </div>

      {error && <div className="panel-error">{error}</div>}

      {stats && (
        <div className="board-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_issues}</span>
            <span className="stat-label">Total Issues</span>
          </div>
          {Object.entries(stats.by_state).slice(0, 4).map(([state, count]) => (
            <div key={state} className="stat-card">
              <span className="stat-value">{count}</span>
              <span className="stat-label">{STATE_NAMES[state]}</span>
            </div>
          ))}
        </div>
      )}

      {autopilotRules.length > 0 && (
        <div className="autopilot-section">
          <h3>Active Autopilot Rules</h3>
          <div className="autopilot-list">
            {autopilotRules.map(rule => (
              <div key={rule.id} className="autopilot-item">
                <div>
                  <strong>{rule.name}</strong>
                  <span className="autopilot-meta">Agent: {rule.agent_id}, Max: {rule.max_concurrent}</span>
                </div>
                <button
                  className="btn-danger btn-sm"
                  onClick={() => handleDeleteAutopilot(rule.id)}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="kanban-board">
        {Object.entries(columns).map(([state, issues]) => (
          <div key={state} className="kanban-column">
            <div className="kanban-column-header" style={{ borderBottomColor: STATE_COLORS[state] }}>
              <span>
                {STATE_EMOJIS[state]} {STATE_NAMES[state]} ({issues.length})
              </span>
            </div>
            <div className="kanban-column-content">
              {issues.map(issue => (
                <div
                  key={issue.id}
                  className={`kanban-card ${selectedIssue?.id === issue.id ? 'selected' : ''}`}
                  onClick={() => setSelectedIssue(issue)}
                >
                  <div className="kanban-card-header">
                    <span
                      className="priority-badge"
                      style={{ backgroundColor: PRIORITY_COLORS[issue.priority] }}
                    >
                      {PRIORITY_EMOJIS[issue.priority]}
                    </span>
                    <h4 className="kanban-card-title">{issue.title}</h4>
                  </div>
                  {issue.description && (
                    <p className="kanban-card-description">{issue.description}</p>
                  )}
                  {issue.tags.length > 0 && (
                    <div className="tag-list">
                      {issue.tags.map((tag, idx) => (
                        <span key={idx} className="tag">{tag}</span>
                      ))}
                    </div>
                  )}
                  {issue.agent_id && (
                    <div className="kanban-card-footer">
                      <span className="agent-badge">👤 {issue.agent_name || issue.agent_id}</span>
                    </div>
                  )}
                  <div className="kanban-card-actions">
                    {state !== 'todo' && (
                      <button
                        className="btn-sm btn-secondary"
                        onClick={(e) => { e.stopPropagation(); handleMoveIssue(issue, 'todo'); }}
                        title="Move to To Do"
                      >
                        ← Todo
                      </button>
                    )}
                    {state !== 'in_progress' && (
                      <button
                        className="btn-sm btn-secondary"
                        onClick={(e) => { e.stopPropagation(); handleMoveIssue(issue, 'in_progress'); }}
                        title="Start Progress"
                      >
                        ▶ Start
                      </button>
                    )}
                    {state !== 'done' && (
                      <button
                        className="btn-sm btn-success"
                        onClick={(e) => { e.stopPropagation(); handleCompleteIssue(issue); }}
                        title="Complete"
                      >
                        ✓ Done
                      </button>
                    )}
                    <button
                      className="btn-sm btn-danger"
                      onClick={(e) => { e.stopPropagation(); handleDeleteIssue(issue.id); }}
                      title="Delete"
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))}
              {issues.length === 0 && (
                <div className="kanban-empty">No issues</div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Create Issue Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>New Issue</h2>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                placeholder="Issue title"
                value={newIssue.title}
                onChange={(e) => setNewIssue({ ...newIssue, title: e.target.value })}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                placeholder="Issue description"
                value={newIssue.description}
                onChange={(e) => setNewIssue({ ...newIssue, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Priority</label>
              <select
                value={newIssue.priority}
                onChange={(e) => setNewIssue({ ...newIssue, priority: e.target.value })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                placeholder="bug, feature, documentation"
                onChange={(e) => setNewIssue({
                  ...newIssue,
                  tags: e.target.value.split(',').map(t => t.trim()).filter(t => t),
                })}
              />
            </div>
            <div className="form-group">
              <label>Assign to Agent ID (optional)</label>
              <input
                type="text"
                placeholder="agent-id"
                value={newIssue.agent_id}
                onChange={(e) => setNewIssue({ ...newIssue, agent_id: e.target.value })}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleCreate}>
                Create Issue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Autopilot Modal */}
      {showAutopilot && (
        <div className="modal-overlay" onClick={() => setShowAutopilot(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Autopilot Configuration</h2>
            <p className="modal-help">
              Autopilot automatically assigns and processes new issues matching your filters.
            </p>
            <div className="form-group">
              <label>Rule Name</label>
              <input
                type="text"
                placeholder="Auto-processing rule"
                value={newAutopilot.name}
                onChange={(e) => setNewAutopilot({ ...newAutopilot, name: e.target.value })}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Agent ID</label>
              <input
                type="text"
                placeholder="agent-id"
                value={newAutopilot.agent_id}
                onChange={(e) => setNewAutopilot({ ...newAutopilot, agent_id: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Max Concurrent Issues</label>
              <input
                type="number"
                min={1}
                max={20}
                value={newAutopilot.max_concurrent}
                onChange={(e) => setNewAutopilot({ ...newAutopilot, max_concurrent: parseInt(e.target.value) })}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowAutopilot(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleCreateAutopilot}>
                Create Rule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
