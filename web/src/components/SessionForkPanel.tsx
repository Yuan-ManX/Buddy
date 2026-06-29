import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#2563eb',
  secondary: '#93c5fd',
  bg: '#eff6ff',
  border: '#bfdbfe',
  accent: '#dbeafe',
  text: '#1e3a8a',
};

const FORK_STRATEGIES = ['shallow', 'deep', 'lazy', 'selective'];
const MERGE_STRATEGIES = ['append', 'interleave', 'replace', 'cherry_pick', 'squash'];
const CONFLICT_POLICIES = ['prefer_fork', 'prefer_original', 'prefer_newer', 'manual_resolve', 'fail_fast'];

export const SessionForkPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'create' | 'fork' | 'merge'>('overview');

  // Sessions list
  const [sessions, setSessions] = useState<any[]>([]);

  // Create form (root session)
  const [createForm, setCreateForm] = useState({
    session_id: '',
    tags: '',
  });

  // Fork form
  const [forkForm, setForkForm] = useState({
    source_session_id: '',
    new_session_id: '',
    strategy: 'shallow',
    reason: '',
  });

  // Message append form
  const [messageForm, setMessageForm] = useState({
    session_id: '',
    role: 'user',
    content: '',
    tokens: '',
  });

  // Merge form
  const [mergeForm, setMergeForm] = useState({
    fork_session_id: '',
    target_session_id: '',
    strategy: 'append',
    conflict_policy: 'prefer_fork',
  });
  const [mergeResult, setMergeResult] = useState<any>(null);

  // Selected session detail
  const [selectedSession, setSelectedSession] = useState<any | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [s, list] = await Promise.all([
        api.sessionFork.stats(),
        api.sessionFork.listSessions(),
      ]);
      setStats(s);
      setSessions(Array.isArray(list) ? list : (list?.sessions ?? []));
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load session fork data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateRoot = async () => {
    if (!createForm.session_id.trim()) return;
    try {
      await api.sessionFork.createRoot({
        session_id: createForm.session_id.trim(),
        tags: createForm.tags.split(',').filter(Boolean),
      });
      toast.success(`Session "${createForm.session_id}" created`);
      setCreateForm({ session_id: '', tags: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleFork = async () => {
    if (!forkForm.source_session_id || !forkForm.new_session_id.trim()) return;
    try {
      await api.sessionFork.fork({ ...forkForm });
      toast.success(`Forked to "${forkForm.new_session_id}"`);
      setForkForm({
        source_session_id: '',
        new_session_id: '',
        strategy: 'shallow',
        reason: '',
      });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAppendMessage = async () => {
    if (!messageForm.session_id || !messageForm.content.trim()) return;
    try {
      await api.sessionFork.appendMessage(messageForm.session_id, {
        role: messageForm.role,
        content: messageForm.content,
        tokens: Number(messageForm.tokens),
      });
      toast.success('Message appended');
      setMessageForm({
        session_id: '',
        role: 'user',
        content: '',
        tokens: '',
      });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleMerge = async () => {
    if (!mergeForm.fork_session_id || !mergeForm.target_session_id) return;
    try {
      const result = await api.sessionFork.requestMerge({ ...mergeForm });
      setMergeResult(result);
      toast.success('Merge requested');
    } catch (e: any) { toast.error(e.message); }
  };

  const handleExecuteMerge = async () => {
    if (!mergeResult?.merge_id) return;
    try {
      await api.sessionFork.executeMerge(mergeResult.merge_id);
      toast.success('Merge executed');
      setMergeResult(null);
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleSelectSession = async (id: string) => {
    try {
      const s = await api.sessionFork.getSession(id);
      setSelectedSession(s);
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="forge-panel">
        <div className="panel-header">
          <h2>🌿 Session Fork</h2>
          <p className="panel-subtitle">Git-like branching for agent conversations</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading session fork...</span></div>
      </div>
    );
  }

  return (
    <div
      className="forge-panel"
      style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}
    >
      <div className="panel-header">
        <h2>🌿 Session Fork</h2>
        <p className="panel-subtitle">Git-like branching for agent conversations</p>
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button>
          </div>
        )}
      </div>

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'create', 'fork', 'merge'] as const).map(s => (
          <button
            key={s}
            className={`forge-tab ${activeSection === s ? 'active' : ''}`}
            onClick={() => setActiveSection(s)}
            style={activeSection === s ? { background: themeColors.primary, borderColor: themeColors.primary } : {}}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeSection === 'overview' && stats && (
        <div className="forge-section">
          <div className="forge-card" style={{ background: themeColors.bg, border: `1px solid ${themeColors.border}` }}>
            <h3 style={{ color: themeColors.text }}>Session Fork Overview</h3>
            <div className="forge-grid">
              <div className="forge-stat">
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_sessions ?? 0}</div>
              </div>
              <div className="forge-stat">
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Messages</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_messages ?? 0}</div>
              </div>
              <div className="forge-stat">
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Forks</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.active_forks ?? 0}</div>
              </div>
              <div className="forge-stat">
                <div style={{ fontWeight: 600, color: themeColors.text }}>Avg Depth</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.avg_depth ?? 0}</div>
              </div>
            </div>
          </div>

          <div className="forge-card" style={{ marginTop: 16 }}>
            <h3 style={{ color: themeColors.text }}>Sessions</h3>
            <table className="forge-table">
              <thead>
                <tr>
                  <th>session_id</th>
                  <th>role</th>
                  <th>status</th>
                  <th>depth</th>
                  <th>message_count</th>
                </tr>
              </thead>
              <tbody>
                {sessions.length === 0 && (
                  <tr><td colSpan={5} style={{ textAlign: 'center', padding: 12 }}>No sessions yet</td></tr>
                )}
                {sessions.map((s, i) => (
                  <tr
                    key={s.session_id ?? i}
                    onClick={() => handleSelectSession(s.session_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>{s.session_id ?? '-'}</td>
                    <td>{s.role ?? '-'}</td>
                    <td>{s.status ?? '-'}</td>
                    <td>{s.depth ?? 0}</td>
                    <td>{s.message_count ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedSession && (
            <div className="forge-card" style={{ marginTop: 16, background: themeColors.bg, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Session Detail: {selectedSession.session_id}</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>
                {JSON.stringify(selectedSession, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Create */}
      {activeSection === 'create' && (
        <div className="forge-section">
          <div className="forge-card">
            <h3 style={{ color: themeColors.text }}>Create Root Session</h3>
            <div className="forge-form">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  className="forge-input"
                  type="text"
                  value={createForm.session_id}
                  onChange={e => setCreateForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="e.g. session-001"
                />
              </div>
              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input
                  className="forge-input"
                  type="text"
                  value={createForm.tags}
                  onChange={e => setCreateForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="e.g. experiment, demo"
                />
              </div>
              <button
                className="forge-btn"
                style={{ background: themeColors.primary }}
                onClick={handleCreateRoot}
                disabled={!createForm.session_id.trim()}
              >
                Create Root Session
              </button>
            </div>
          </div>

          <div className="forge-card" style={{ marginTop: 16 }}>
            <h3 style={{ color: themeColors.text }}>Append Message</h3>
            <div className="forge-form">
              <div className="form-group">
                <label>Session *</label>
                <select
                  className="forge-select"
                  value={messageForm.session_id}
                  onChange={e => setMessageForm(f => ({ ...f, session_id: e.target.value }))}
                >
                  <option value="">-- select session --</option>
                  {sessions.map((s, i) => (
                    <option key={s.session_id ?? i} value={s.session_id}>{s.session_id}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  className="forge-select"
                  value={messageForm.role}
                  onChange={e => setMessageForm(f => ({ ...f, role: e.target.value }))}
                >
                  <option value="user">user</option>
                  <option value="assistant">assistant</option>
                  <option value="system">system</option>
                  <option value="tool">tool</option>
                </select>
              </div>
              <div className="form-group">
                <label>Content *</label>
                <textarea
                  className="forge-input"
                  rows={4}
                  value={messageForm.content}
                  onChange={e => setMessageForm(f => ({ ...f, content: e.target.value }))}
                  placeholder="Message content..."
                />
              </div>
              <div className="form-group">
                <label>Tokens</label>
                <input
                  className="forge-input"
                  type="number"
                  min="0"
                  value={messageForm.tokens}
                  onChange={e => setMessageForm(f => ({ ...f, tokens: e.target.value }))}
                  placeholder="Token count"
                />
              </div>
              <button
                className="forge-btn"
                style={{ background: themeColors.primary }}
                onClick={handleAppendMessage}
                disabled={!messageForm.session_id || !messageForm.content.trim()}
              >
                Append Message
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fork */}
      {activeSection === 'fork' && (
        <div className="forge-section">
          <div className="forge-card">
            <h3 style={{ color: themeColors.text }}>Fork Session</h3>
            <div className="forge-form">
              <div className="form-group">
                <label>Source Session *</label>
                <select
                  className="forge-select"
                  value={forkForm.source_session_id}
                  onChange={e => setForkForm(f => ({ ...f, source_session_id: e.target.value }))}
                >
                  <option value="">-- select source --</option>
                  {sessions.map((s, i) => (
                    <option key={s.session_id ?? i} value={s.session_id}>{s.session_id}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>New Session ID *</label>
                <input
                  className="forge-input"
                  type="text"
                  value={forkForm.new_session_id}
                  onChange={e => setForkForm(f => ({ ...f, new_session_id: e.target.value }))}
                  placeholder="e.g. session-001-fork-a"
                />
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select
                  className="forge-select"
                  value={forkForm.strategy}
                  onChange={e => setForkForm(f => ({ ...f, strategy: e.target.value }))}
                >
                  {FORK_STRATEGIES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Reason</label>
                <textarea
                  className="forge-input"
                  rows={3}
                  value={forkForm.reason}
                  onChange={e => setForkForm(f => ({ ...f, reason: e.target.value }))}
                  placeholder="Why are you forking this session?"
                />
              </div>
              <button
                className="forge-btn"
                style={{ background: themeColors.primary }}
                onClick={handleFork}
                disabled={!forkForm.source_session_id || !forkForm.new_session_id.trim()}
              >
                Fork Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge */}
      {activeSection === 'merge' && (
        <div className="forge-section">
          <div className="forge-card">
            <h3 style={{ color: themeColors.text }}>Request Merge</h3>
            <div className="forge-form">
              <div className="form-group">
                <label>Fork Session *</label>
                <select
                  className="forge-select"
                  value={mergeForm.fork_session_id}
                  onChange={e => setMergeForm(f => ({ ...f, fork_session_id: e.target.value }))}
                >
                  <option value="">-- select fork session --</option>
                  {sessions.map((s, i) => (
                    <option key={s.session_id ?? i} value={s.session_id}>{s.session_id}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Target Session *</label>
                <select
                  className="forge-select"
                  value={mergeForm.target_session_id}
                  onChange={e => setMergeForm(f => ({ ...f, target_session_id: e.target.value }))}
                >
                  <option value="">-- select target session --</option>
                  {sessions.map((s, i) => (
                    <option key={s.session_id ?? i} value={s.session_id}>{s.session_id}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Strategy</label>
                <select
                  className="forge-select"
                  value={mergeForm.strategy}
                  onChange={e => setMergeForm(f => ({ ...f, strategy: e.target.value }))}
                >
                  {MERGE_STRATEGIES.map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Conflict Policy</label>
                <select
                  className="forge-select"
                  value={mergeForm.conflict_policy}
                  onChange={e => setMergeForm(f => ({ ...f, conflict_policy: e.target.value }))}
                >
                  {CONFLICT_POLICIES.map(p => (
                    <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
              <button
                className="forge-btn"
                style={{ background: themeColors.primary }}
                onClick={handleMerge}
                disabled={!mergeForm.fork_session_id || !mergeForm.target_session_id}
              >
                Request Merge
              </button>
            </div>
          </div>

          {mergeResult && (
            <div className="forge-card" style={{ marginTop: 16, background: themeColors.bg, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Merge Result</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>
                {JSON.stringify(mergeResult, null, 2)}
              </pre>
              <button
                className="forge-btn"
                style={{ background: themeColors.primary, marginTop: 12 }}
                onClick={handleExecuteMerge}
              >
                Execute Merge
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SessionForkPanel;
