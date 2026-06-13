import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

interface KanbanIssue {
  id: string;
  title: string;
  description?: string;
  state: string;
  priority?: string;
  agent_id?: string;
  tags?: string[];
  created_at?: string;
  updated_at?: string;
}

interface KanbanColumn {
  id: string;
  title: string;
  state: string;
  issues: KanbanIssue[];
}

const COLUMNS: KanbanColumn[] = [
  { id: 'backlog', title: 'Backlog', state: 'backlog', issues: [] },
  { id: 'todo', title: 'To Do', state: 'todo', issues: [] },
  { id: 'in_progress', title: 'In Progress', state: 'in_progress', issues: [] },
  { id: 'review', title: 'Review', state: 'review', issues: [] },
  { id: 'done', title: 'Done', state: 'done', issues: [] },
];

export const KanbanBoard: React.FC = () => {
  const [columns, setColumns] = useState<KanbanColumn[]>(COLUMNS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newIssue, setNewIssue] = useState({
    title: '',
    description: '',
    priority: 'medium',
    tags: '' as string,
  });
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [draggingIssue, setDraggingIssue] = useState<KanbanIssue | null>(null);
  const { success: showSuccess, error: showError } = useToast();

  const loadBoard = useCallback(async () => {
    try {
      setLoading(true);
      const [boardRes, issuesRes] = await Promise.all([
        api.board.getBoard(),
        api.board.listIssues({}),
      ]);

      const issues = (issuesRes as any).issues || [];

      const updatedColumns = COLUMNS.map(col => ({
        ...col,
        issues: issues.filter((i: KanbanIssue) => i.state === col.state),
      }));

      setColumns(updatedColumns);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load board');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  const handleDragStart = (issue: KanbanIssue) => {
    setDraggingIssue(issue);
  };

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    setDragOverColumn(columnId);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = async (columnId: string) => {
    setDragOverColumn(null);
    if (!draggingIssue) return;

    const targetColumn = COLUMNS.find(c => c.id === columnId);
    if (!targetColumn || draggingIssue.state === targetColumn.state) {
      setDraggingIssue(null);
      return;
    }

    // Optimistic update
    setColumns(prev =>
      prev.map(col => {
        if (col.id === columnId) {
          return {
            ...col,
            issues: [...col.issues, { ...draggingIssue, state: targetColumn.state }],
          };
        }
        return {
          ...col,
          issues: col.issues.filter(i => i.id !== draggingIssue.id),
        };
      })
    );

    try {
      await api.board.moveIssue(draggingIssue.id, targetColumn.state);
      showSuccess(`Moved to ${targetColumn.title}`);
    } catch (e: any) {
      showError('Failed to move issue');
      loadBoard(); // Revert on error
    }

    setDraggingIssue(null);
  };

  const handleCreateIssue = async () => {
    if (!newIssue.title.trim()) return;

    try {
      await api.board.createIssue({
        title: newIssue.title,
        description: newIssue.description,
        priority: newIssue.priority,
        tags: newIssue.tags ? newIssue.tags.split(',').map(t => t.trim()) : [],
      });
      showSuccess('Issue created');
      setShowCreate(false);
      setNewIssue({ title: '', description: '', priority: 'medium', tags: '' });
      loadBoard();
    } catch (e: any) {
      showError(e.message || 'Failed to create issue');
    }
  };

  const handleDeleteIssue = async (issueId: string) => {
    try {
      await api.board.deleteIssue(issueId);
      showSuccess('Issue deleted');
      loadBoard();
    } catch (e: any) {
      showError('Failed to delete issue');
    }
  };

  const handleClaimIssue = async (issueId: string, agentId: string) => {
    try {
      await api.board.claimIssue(issueId, agentId);
      showSuccess('Issue claimed');
      loadBoard();
    } catch (e: any) {
      showError('Failed to claim issue');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'var(--red)';
      case 'high': return 'var(--amber)';
      case 'medium': return 'var(--blue)';
      case 'low': return 'var(--green)';
      default: return 'var(--text-muted)';
    }
  };

  const getColumnIssueCount = (col: KanbanColumn) => col.issues.length;

  if (loading) {
    return <div className="panel"><div className="panel-loading">Loading board...</div></div>;
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Kanban Board</h2>
        <div className="panel-header-actions">
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + New Issue
          </button>
          <button className="btn-secondary" onClick={loadBoard}>Refresh</button>
        </div>
      </div>

      {error && (
        <div className="panel-error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>Create Issue</h2>
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                placeholder="Issue title"
                value={newIssue.title}
                onChange={e => setNewIssue({ ...newIssue, title: e.target.value })}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                placeholder="Issue description (optional)"
                value={newIssue.description}
                onChange={e => setNewIssue({ ...newIssue, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Priority</label>
              <select
                value={newIssue.priority}
                onChange={e => setNewIssue({ ...newIssue, priority: e.target.value })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                placeholder="e.g., bug, feature, urgent"
                value={newIssue.tags}
                onChange={e => setNewIssue({ ...newIssue, tags: e.target.value })}
              />
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreateIssue}>Create</button>
            </div>
          </div>
        </div>
      )}

      <div className="kanban-board">
        {columns.map(col => (
          <div
            key={col.id}
            className={`kanban-column ${dragOverColumn === col.id ? 'drag-over' : ''}`}
            onDragOver={e => handleDragOver(e, col.id)}
            onDragLeave={handleDragLeave}
            onDrop={() => handleDrop(col.id)}
          >
            <div className="kanban-column-header">
              <div className="kanban-column-title">
                <span className="kanban-column-dot" style={{
                  backgroundColor: col.state === 'done' ? 'var(--green)'
                    : col.state === 'in_progress' ? 'var(--blue)'
                    : col.state === 'review' ? 'var(--amber)'
                    : 'var(--text-muted)'
                }} />
                {col.title}
              </div>
              <span className="kanban-column-count">{getColumnIssueCount(col)}</span>
            </div>

            <div className="kanban-column-body">
              {col.issues.length === 0 && (
                <div className="kanban-empty">
                  Drop issues here
                </div>
              )}
              {col.issues.map(issue => (
                <div
                  key={issue.id}
                  className="kanban-card"
                  draggable
                  onDragStart={() => handleDragStart(issue)}
                >
                  <div className="kanban-card-header">
                    <span
                      className="kanban-card-priority"
                      style={{ backgroundColor: getPriorityColor(issue.priority || 'medium') }}
                    />
                    <span className="kanban-card-title">{issue.title}</span>
                  </div>
                  {issue.description && (
                    <div className="kanban-card-desc">
                      {issue.description.length > 100
                        ? issue.description.substring(0, 100) + '...'
                        : issue.description}
                    </div>
                  )}
                  <div className="kanban-card-footer">
                    <div className="kanban-card-meta">
                      {issue.tags && issue.tags.map((tag, i) => (
                        <span key={i} className="kanban-tag">{tag}</span>
                      ))}
                    </div>
                    <div className="kanban-card-actions">
                      {issue.state === 'todo' && !issue.agent_id && (
                        <button
                          className="kanban-btn-claim"
                          title="Claim this issue"
                          onClick={() => handleClaimIssue(issue.id, '')}
                        >
                          Claim
                        </button>
                      )}
                      <button
                        className="kanban-btn-delete"
                        title="Delete"
                        onClick={() => handleDeleteIssue(issue.id)}
                      >
                        ×
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};