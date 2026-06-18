import React, { useState, useEffect, useCallback } from 'react';
import { useToast } from './Toast';

interface CollabStats {
  rooms: { total: number; by_type: Record<string, number>; by_state: Record<string, number> };
  sessions: { total: number; active: number; completed: number };
  artifacts: { total: number; by_type: Record<string, number> };
  consensus: { total_proposals: number; approved: number; rejected: number };
}

interface CollabRoom {
  room_id: string;
  name: string;
  room_type: string;
  state: string;
  agent_count: number;
  session_count: number;
}

export const CollabSpacePanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<CollabStats | null>(null);
  const [rooms, setRooms] = useState<CollabRoom[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'rooms' | 'create' | 'sessions' | 'proposals'>('overview');

  // Create room form
  const [roomForm, setRoomForm] = useState({
    name: '',
    room_type: 'general',
    created_by: '',
    description: '',
    max_agents: '10',
  });

  // Create session form
  const [selectedRoomId, setSelectedRoomId] = useState('');
  const [sessionForm, setSessionForm] = useState({ title: '', created_by: '' });

  // Proposal form
  const [proposalForm, setProposalForm] = useState({
    room_id: '',
    title: '',
    description: '',
    proposed_by: '',
    options: '',
    consensus_type: 'majority',
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsRes, roomsRes] = await Promise.all([
        fetch('/api/collab/stats'),
        fetch('/api/collab/rooms'),
      ]);
      const s = await statsRes.json();
      const r = await roomsRes.json();
      setStats(s);
      setRooms(r.rooms || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateRoom = async () => {
    try {
      const res = await fetch('/api/collab/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...roomForm, max_agents: parseInt(roomForm.max_agents) || 10 }),
      });
      const data = await res.json();
      toast?.success?.('Room created: ' + data.room_id);
      setRoomForm({ name: '', room_type: 'general', created_by: '', description: '', max_agents: '10' });
      loadData();
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleCreateSession = async () => {
    try {
      const res = await fetch(`/api/collab/rooms/${selectedRoomId}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sessionForm),
      });
      const data = await res.json();
      toast?.success?.('Session created: ' + data.session_id);
      setSessionForm({ title: '', created_by: '' });
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  const handleCreateProposal = async () => {
    try {
      const res = await fetch(`/api/collab/rooms/${proposalForm.room_id}/proposals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...proposalForm,
          options: proposalForm.options ? proposalForm.options.split(',').map(s => s.trim()) : [],
        }),
      });
      const data = await res.json();
      toast?.success?.('Proposal created: ' + data.proposal_id);
      setProposalForm({ room_id: '', title: '', description: '', proposed_by: '', options: '', consensus_type: 'majority' });
    } catch (e: any) {
      toast?.error?.('Failed: ' + e.message);
    }
  };

  if (loading) return <div className="panel loading">Loading collaboration space...</div>;

  return (
    <div className="panel collab-panel">
      <div className="panel-header">
        <h2>Collaboration Space</h2>
        <span className="panel-badge">
          {stats ? `${stats.rooms?.total || 0} rooms` : 'Loading'}
        </span>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="panel-tabs">
        {(['overview', 'rooms', 'create', 'sessions', 'proposals'] as const).map((s) => (
          <button
            key={s}
            className={`panel-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="panel-content">
        {activeSection === 'overview' && stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.rooms?.total || 0}</div>
              <div className="stat-label">Total Rooms</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.sessions?.total || 0}</div>
              <div className="stat-label">Total Sessions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.sessions?.active || 0}</div>
              <div className="stat-label">Active Sessions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.artifacts?.total || 0}</div>
              <div className="stat-label">Artifacts</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.consensus?.total_proposals || 0}</div>
              <div className="stat-label">Proposals</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.consensus?.approved || 0}</div>
              <div className="stat-label">Approved</div>
            </div>

            {stats.rooms?.by_type && (
              <div className="section-card full-width">
                <h3>Room Types</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.rooms.by_type).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.rooms.by_type).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.rooms?.by_state && (
              <div className="section-card full-width">
                <h3>Room States</h3>
                <div className="distribution-bars">
                  {Object.entries(stats.rooms.by_state).map(([k, v]) => (
                    <div key={k} className="dist-row">
                      <span className="dist-label">{k}</span>
                      <div className="dist-bar-container">
                        <div className="dist-bar" style={{ width: `${Math.min((Number(v) / Math.max(...Object.values(stats.rooms.by_state).map(Number)) || 1) * 100, 100)}%` }} />
                      </div>
                      <span className="dist-value">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'rooms' && (
          <div className="section-card">
            <h3>Collaboration Rooms</h3>
            {rooms.length === 0 ? (
              <p className="empty-text">No rooms yet. Create one to get started.</p>
            ) : (
              <div className="room-list">
                {rooms.map((room) => (
                  <div key={room.room_id} className="room-card">
                    <div className="room-name">{room.name}</div>
                    <div className="room-meta">
                      <span className={`room-type-badge ${room.room_type}`}>{room.room_type}</span>
                      <span className={`room-state-badge ${room.state}`}>{room.state}</span>
                      <span>{room.agent_count} agents</span>
                      <span>{room.session_count} sessions</span>
                    </div>
                    <div className="room-id">ID: {room.room_id}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSection === 'create' && (
          <div className="form-section">
            <h3>Create Collaboration Room</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Room Name</label>
                <input type="text" value={roomForm.name} onChange={e => setRoomForm({ ...roomForm, name: e.target.value })} placeholder="My Room" />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={roomForm.room_type} onChange={e => setRoomForm({ ...roomForm, room_type: e.target.value })}>
                  <option value="general">General</option>
                  <option value="brainstorm">Brainstorm</option>
                  <option value="review">Review</option>
                  <option value="planning">Planning</option>
                  <option value="debug">Debug</option>
                </select>
              </div>
              <div className="form-group">
                <label>Created By</label>
                <input type="text" value={roomForm.created_by} onChange={e => setRoomForm({ ...roomForm, created_by: e.target.value })} placeholder="agent-..." />
              </div>
              <div className="form-group">
                <label>Max Agents</label>
                <input type="number" value={roomForm.max_agents} onChange={e => setRoomForm({ ...roomForm, max_agents: e.target.value })} min="2" max="50" />
              </div>
              <div className="form-group full-width">
                <label>Description</label>
                <textarea value={roomForm.description} onChange={e => setRoomForm({ ...roomForm, description: e.target.value })} placeholder="Room description..." rows={3} />
              </div>
            </div>
            <button className="btn-primary" onClick={handleCreateRoom}>Create Room</button>
          </div>
        )}

        {activeSection === 'sessions' && (
          <div className="form-section">
            <h3>Create Session</h3>
            <div className="form-group">
              <label>Room ID</label>
              <select value={selectedRoomId} onChange={e => setSelectedRoomId(e.target.value)}>
                <option value="">Select a room...</option>
                {rooms.map(r => (
                  <option key={r.room_id} value={r.room_id}>{r.name} ({r.room_id})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Session Title</label>
              <input type="text" value={sessionForm.title} onChange={e => setSessionForm({ ...sessionForm, title: e.target.value })} placeholder="Session title..." />
            </div>
            <div className="form-group">
              <label>Created By</label>
              <input type="text" value={sessionForm.created_by} onChange={e => setSessionForm({ ...sessionForm, created_by: e.target.value })} placeholder="agent-..." />
            </div>
            <button className="btn-primary" onClick={handleCreateSession} disabled={!selectedRoomId}>Create Session</button>
          </div>
        )}

        {activeSection === 'proposals' && (
          <div className="form-section">
            <h3>Create Consensus Proposal</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Room ID</label>
                <select value={proposalForm.room_id} onChange={e => setProposalForm({ ...proposalForm, room_id: e.target.value })}>
                  <option value="">Select a room...</option>
                  {rooms.map(r => (
                    <option key={r.room_id} value={r.room_id}>{r.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Title</label>
                <input type="text" value={proposalForm.title} onChange={e => setProposalForm({ ...proposalForm, title: e.target.value })} placeholder="Proposal title..." />
              </div>
              <div className="form-group">
                <label>Proposed By</label>
                <input type="text" value={proposalForm.proposed_by} onChange={e => setProposalForm({ ...proposalForm, proposed_by: e.target.value })} placeholder="agent-..." />
              </div>
              <div className="form-group">
                <label>Consensus Type</label>
                <select value={proposalForm.consensus_type} onChange={e => setProposalForm({ ...proposalForm, consensus_type: e.target.value })}>
                  <option value="majority">Majority</option>
                  <option value="unanimous">Unanimous</option>
                  <option value="weighted">Weighted</option>
                </select>
              </div>
              <div className="form-group full-width">
                <label>Description</label>
                <textarea value={proposalForm.description} onChange={e => setProposalForm({ ...proposalForm, description: e.target.value })} placeholder="Describe the proposal..." rows={3} />
              </div>
              <div className="form-group full-width">
                <label>Options (comma-separated)</label>
                <input type="text" value={proposalForm.options} onChange={e => setProposalForm({ ...proposalForm, options: e.target.value })} placeholder="Option A, Option B, Option C" />
              </div>
            </div>
            <button className="btn-primary" onClick={handleCreateProposal} disabled={!proposalForm.room_id}>Create Proposal</button>
          </div>
        )}
      </div>
    </div>
  );
};