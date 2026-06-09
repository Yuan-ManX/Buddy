import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';
import type { Agent, Squad, SquadMember } from '../types';

interface Props {
  agent: Agent;
}

export const SquadsPanel: React.FC<Props> = ({ agent }) => {
  const [squads, setSquads] = useState<Squad[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSquad, setSelectedSquad] = useState<Squad | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [squadName, setSquadName] = useState('');
  const [squadDesc, setSquadDesc] = useState('');
  const [showAddMember, setShowAddMember] = useState(false);
  const [memberAgentId, setMemberAgentId] = useState('');
  const [memberName, setMemberName] = useState('');
  const [memberRole, setMemberRole] = useState('generalist');
  const [memberExpertise, setMemberExpertise] = useState('');
  const [discussionTopic, setDiscussionTopic] = useState('');
  const [discussionPost, setDiscussionPost] = useState('');
  const toast = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      const s = await api.squads.list();
      setSquads(Array.isArray(s) ? s : []);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load squads');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateSquad = async () => {
    if (!squadName.trim()) return;
    try {
      const squad = await api.squads.form({
        name: squadName.trim(),
        description: squadDesc,
        leader_id: agent.id,
      });
      toast.success(`Squad "${squadName}" created`);
      setSquadName('');
      setSquadDesc('');
      setShowCreate(false);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleActivateSquad = async (squadId: string) => {
    try {
      await api.squads.activate(squadId);
      toast.success('Squad activated');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handlePauseSquad = async (squadId: string) => {
    try {
      await api.squads.pause(squadId);
      toast.success('Squad paused');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleDissolveSquad = async (squadId: string) => {
    if (!confirm('Dissolve this squad?')) return;
    try {
      await api.squads.dissolve(squadId);
      toast.success('Squad dissolved');
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleAddMember = async () => {
    if (!selectedSquad || !memberAgentId.trim()) return;
    try {
      await api.squads.addMember(
        selectedSquad.squad_id,
        memberAgentId.trim(),
        memberName,
        memberRole,
        memberExpertise,
      );
      toast.success('Member added');
      setMemberAgentId('');
      setMemberName('');
      setMemberExpertise('');
      setShowAddMember(false);
      const updated = await api.squads.get(selectedSquad.squad_id);
      setSelectedSquad(updated);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleRemoveMember = async (squadId: string, memberId: string) => {
    try {
      await api.squads.removeMember(squadId, memberId);
      toast.success('Member removed');
      const updated = await api.squads.get(squadId);
      setSelectedSquad(updated);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const handleStartDiscussion = async () => {
    if (!selectedSquad || !discussionTopic.trim()) return;
    try {
      await api.squads.startDiscussion(selectedSquad.squad_id, discussionTopic.trim(), agent.id);
      toast.success('Discussion started');
      setDiscussionTopic('');
      const updated = await api.squads.get(selectedSquad.squad_id);
      setSelectedSquad(updated);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return '#10b981';
      case 'paused': return '#f59e0b';
      case 'dissolved': return '#ef4444';
      default: return '#94a3b8';
    }
  };

  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      leader: 'Leader',
      generalist: 'Generalist',
      specialist: 'Specialist',
      reviewer: 'Reviewer',
      executor: 'Executor',
    };
    return labels[role] || role;
  };

  if (loading) return (
    <div className="panel-container">
      <div className="panel-loading">
        <div className="dashboard-spinner"></div>
        <div>Loading squads...</div>
      </div>
    </div>
  );

  if (error) return (
    <div className="panel-container">
      <div className="error-banner">
        {error}
        <button onClick={loadData} className="btn-sm" style={{ marginLeft: '8px' }}>Retry</button>
      </div>
    </div>
  );

  return (
    <div className="panel-container">
      <div className="panel-header">
        <div>
          <h2>Buddy Squads</h2>
          <div className="panel-subtitle">Collaborative Agent Teams</div>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>
          Form Squad
        </button>
      </div>

      {/* Create Squad Form */}
      {showCreate && (
        <div className="dashboard-section">
          <h3>Form New Squad</h3>
          <div className="form-group">
            <label>Squad Name</label>
            <input
              type="text"
              placeholder="e.g., Development Strike Team"
              value={squadName}
              onChange={e => setSquadName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea
              placeholder="What does this squad do?"
              value={squadDesc}
              onChange={e => setSquadDesc(e.target.value)}
              rows={2}
            />
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn-primary" onClick={handleCreateSquad}>Create</button>
            <button className="btn-secondary" onClick={() => { setShowCreate(false); setSquadName(''); setSquadDesc(''); }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Squad Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedSquad ? '1fr 1fr' : '1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          {squads.length === 0 ? (
            <div className="panel-empty">No squads formed yet</div>
          ) : (
            <div className="forge-skill-list">
              {squads.map(squad => (
                <div
                  key={squad.squad_id}
                  className={`forge-skill-card ${selectedSquad?.squad_id === squad.squad_id ? '' : ''}`}
                  onClick={() => setSelectedSquad(squad)}
                  style={{ cursor: 'pointer', borderColor: selectedSquad?.squad_id === squad.squad_id ? 'var(--blue)' : undefined }}
                >
                  <div className="forge-skill-header">
                    <div className="forge-skill-name">{squad.name}</div>
                    <div className="dashboard-badge" style={{ background: `${getStatusColor(squad.status)}15`, color: getStatusColor(squad.status) }}>
                      {squad.status}
                    </div>
                  </div>
                  <div className="forge-skill-meta">
                    {squad.description && <div>{squad.description}</div>}
                    <div>
                      <span>Members: {squad.member_count}</span> ·
                      <span> Tasks: {squad.total_tasks}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                    {squad.status !== 'dissolved' && (
                      <>
                        <button className="btn-sm btn-success" onClick={(e) => { e.stopPropagation(); handleActivateSquad(squad.squad_id); }}>
                          Activate
                        </button>
                        <button className="btn-sm" onClick={(e) => { e.stopPropagation(); handlePauseSquad(squad.squad_id); }}>
                          Pause
                        </button>
                      </>
                    )}
                    <button className="btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDissolveSquad(squad.squad_id); }}>
                      Dissolve
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Squad Detail */}
        {selectedSquad && (
          <div className="dashboard-section" style={{ marginTop: 0 }}>
            <h3>{selectedSquad.name}</h3>
            {selectedSquad.description && (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                {selectedSquad.description}
              </p>
            )}

            {/* Members */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div className="text-xs font-bold" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Members ({selectedSquad.members?.length || 0})
                </div>
                <button className="btn-sm" onClick={() => setShowAddMember(!showAddMember)}>
                  {showAddMember ? 'Cancel' : 'Add Member'}
                </button>
              </div>

              {showAddMember && (
                <div style={{ background: 'var(--bg-elevated)', padding: '12px', borderRadius: '8px', marginBottom: '12px' }}>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Agent ID</label>
                      <input type="text" placeholder="agent-..." value={memberAgentId} onChange={e => setMemberAgentId(e.target.value)} />
                    </div>
                    <div className="form-group">
                      <label>Name</label>
                      <input type="text" placeholder="Agent name" value={memberName} onChange={e => setMemberName(e.target.value)} />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Role</label>
                      <select value={memberRole} onChange={e => setMemberRole(e.target.value)}>
                        {['generalist', 'specialist', 'reviewer', 'executor'].map(r => (
                          <option key={r} value={r}>{getRoleLabel(r)}</option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Expertise (comma-separated)</label>
                      <input type="text" placeholder="e.g., Python, React" value={memberExpertise} onChange={e => setMemberExpertise(e.target.value)} />
                    </div>
                  </div>
                  <button className="btn-primary btn-sm" onClick={handleAddMember}>Add</button>
                </div>
              )}

              {selectedSquad.members?.map(member => (
                <div key={member.agent_id} className="dashboard-agent-card">
                  <div className="dashboard-agent-avatar" style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
                    {member.agent_name?.charAt(0)?.toUpperCase() || '?'}
                  </div>
                  <div className="dashboard-agent-info">
                    <div className="dashboard-agent-name">{member.agent_name || member.agent_id}</div>
                    <div className="dashboard-agent-role">{getRoleLabel(member.role)} · Trust: {(member.trust_score * 100).toFixed(0)}%</div>
                  </div>
                  {member.trust_score !== undefined && (
                    <div style={{ width: '80px' }}>
                      <div className="text-xs text-muted" style={{ textAlign: 'right', marginBottom: '2px' }}>
                        {member.tasks_completed}/{member.tasks_completed + member.tasks_failed} tasks
                      </div>
                      <div className="dashboard-progress-bar">
                        <div
                          className="dashboard-progress-fill"
                          style={{
                            width: `${member.success_rate * 100}%`,
                            background: member.success_rate >= 0.7 ? '#10b981' : member.success_rate >= 0.4 ? '#f59e0b' : '#ef4444',
                          }}
                        />
                      </div>
                    </div>
                  )}
                  <button
                    className="btn-sm btn-danger"
                    style={{ marginLeft: '8px' }}
                    onClick={() => handleRemoveMember(selectedSquad.squad_id, member.agent_id)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>

            {/* Discussions */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div className="text-xs font-bold" style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Discussions
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                  type="text"
                  className="panel-search-input"
                  placeholder="New discussion topic..."
                  value={discussionTopic}
                  onChange={e => setDiscussionTopic(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button className="btn-sm" onClick={handleStartDiscussion}>Start</button>
              </div>
              {selectedSquad.discussions?.length === 0 && (
                <div className="text-xs text-muted">No discussions yet</div>
              )}
              {selectedSquad.discussions?.map(thread => (
                <div key={thread.thread_id} className="forge-skill-card" style={{ marginBottom: '8px' }}>
                  <div className="forge-skill-header">
                    <div className="forge-skill-name" style={{ fontSize: '0.85rem' }}>{thread.topic}</div>
                    <div className="dashboard-badge">{thread.status}</div>
                  </div>
                  <div className="forge-skill-meta">
                    <div>Messages: {thread.message_count}</div>
                    {thread.resolution && <div style={{ color: '#10b981', fontSize: '0.8rem' }}>Resolution: {thread.resolution}</div>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};