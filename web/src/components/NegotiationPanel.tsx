import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useToast } from './Toast';

const themeColors = {
  primary: '#2563eb',
  secondary: '#93c5fd',
  bg: '#eff6ff',
  border: '#bfdbfe',
  accent: '#dbeafe',
  text: '#1e3a5f',
};

const STRATEGIES = ['collaborative', 'competitive', 'mediated', 'consensus_driven', 'voting_based'];
const DELEGATE_ROLES = ['proponent', 'opponent', 'mediator', 'observer', 'facilitator', 'expert'];

interface NegotiationStats {
  total_sessions: number;
  total_rounds: number;
  total_proposals: number;
  active_sessions: number;
  resolved_sessions: number;
}

export const NegotiationPanel: React.FC = () => {
  const toast = useToast();
  const [stats, setStats] = useState<NegotiationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'session' | 'delegate' | 'negotiate' | 'resolve'>('overview');

  // Create session form
  const [sessionForm, setSessionForm] = useState({
    topic: '', description: '', strategy: 'collaborative',
  });

  // Add delegate form
  const [delegateForm, setDelegateForm] = useState({
    session_id: '', name: '', role: 'proponent', stance: '', priority: '',
  });

  // Propose form
  const [proposeForm, setProposeForm] = useState({
    session_id: '', delegate_id: '', content: '', rationale: '', confidence: '',
  });

  // Vote form
  const [voteForm, setVoteForm] = useState({
    session_id: '', proposal_id: '', delegate_id: '', approve: true,
  });

  // Deliberate form
  const [deliberateForm, setDeliberateForm] = useState({
    session_id: '', summary: '',
  });

  // Resolve / Summary
  const [resolveSessionId, setResolveSessionId] = useState('');
  const [summarySessionId, setSummarySessionId] = useState('');
  const [summaryResult, setSummaryResult] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const s = await api.negotiation.stats();
      setStats(s);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load negotiation data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateSession = async () => {
    if (!sessionForm.topic.trim()) return;
    try {
      await api.negotiation.createSession({
        topic: sessionForm.topic.trim(),
        description: sessionForm.description || undefined,
        strategy: sessionForm.strategy,
      });
      toast.success(`Negotiation session "${sessionForm.topic}" created`);
      setSessionForm({ topic: '', description: '', strategy: 'collaborative' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleAddDelegate = async () => {
    if (!delegateForm.session_id.trim() || !delegateForm.name.trim()) return;
    try {
      await api.negotiation.addDelegate({
        session_id: delegateForm.session_id.trim(),
        name: delegateForm.name.trim(),
        role: delegateForm.role,
        stance: delegateForm.stance || undefined,
        priority: delegateForm.priority ? Number(delegateForm.priority) : undefined,
      });
      toast.success(`Delegate "${delegateForm.name}" added`);
      setDelegateForm({ session_id: '', name: '', role: 'proponent', stance: '', priority: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handlePropose = async () => {
    if (!proposeForm.session_id.trim() || !proposeForm.delegate_id.trim() || !proposeForm.content.trim()) return;
    try {
      await api.negotiation.propose({
        session_id: proposeForm.session_id.trim(),
        delegate_id: proposeForm.delegate_id.trim(),
        content: proposeForm.content.trim(),
        rationale: proposeForm.rationale || undefined,
        confidence: proposeForm.confidence ? Number(proposeForm.confidence) : undefined,
      });
      toast.success('Proposal submitted');
      setProposeForm({ session_id: '', delegate_id: '', content: '', rationale: '', confidence: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleVote = async () => {
    if (!voteForm.session_id.trim() || !voteForm.proposal_id.trim() || !voteForm.delegate_id.trim()) return;
    try {
      await api.negotiation.vote({
        session_id: voteForm.session_id.trim(),
        proposal_id: voteForm.proposal_id.trim(),
        delegate_id: voteForm.delegate_id.trim(),
        approve: voteForm.approve,
      });
      toast.success('Vote recorded');
      setVoteForm({ session_id: '', proposal_id: '', delegate_id: '', approve: true });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleDeliberate = async () => {
    if (!deliberateForm.session_id.trim() || !deliberateForm.summary.trim()) return;
    try {
      await api.negotiation.deliberate({
        session_id: deliberateForm.session_id.trim(),
        summary: deliberateForm.summary.trim(),
      });
      toast.success('Deliberation submitted');
      setDeliberateForm({ session_id: '', summary: '' });
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleResolve = async () => {
    if (!resolveSessionId.trim()) return;
    try {
      await api.negotiation.resolve(resolveSessionId.trim());
      toast.success('Session resolved');
      setResolveSessionId('');
      loadData();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleGetSummary = async () => {
    if (!summarySessionId.trim()) return;
    try {
      const result = await api.negotiation.summary(summarySessionId.trim());
      setSummaryResult(result);
      toast.success('Summary loaded');
    } catch (e: any) { toast.error(e.message); }
  };

  if (loading) {
    return (
      <div className="panel-container">
        <div className="panel-header">
          <h2>🤝 Negotiation Protocol</h2>
          <p className="panel-subtitle">Multi-agent debate, negotiation, and consensus building</p>
        </div>
        <div className="panel-loading"><div className="spinner" /><span>Loading negotiation protocol...</span></div>
      </div>
    );
  }

  return (
    <div className="panel-container" style={{ '--accent-primary': themeColors.primary, '--accent-secondary': themeColors.secondary } as React.CSSProperties}>
      <div className="panel-header">
        <h2>🤝 Negotiation Protocol</h2>
        <p className="panel-subtitle">Multi-agent debate, negotiation, and consensus building</p>
        {error && <div className="error-banner">{error}<button onClick={loadData} className="btn-sm" style={{ marginLeft: 8 }}>Retry</button></div>}
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_sessions}</span><span className="stat-label">Total Sessions</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_rounds}</span><span className="stat-label">Total Rounds</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: themeColors.primary }}>{stats.total_proposals}</span><span className="stat-label">Total Proposals</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: '#22c55e' }}>{stats.active_sessions}</span><span className="stat-label">Active</span></div></div>
          <div className="stat-item"><div className="stat-content"><span className="stat-value" style={{ color: '#8b5cf6' }}>{stats.resolved_sessions}</span><span className="stat-label">Resolved</span></div></div>
        </div>
      )}

      {/* Section Tabs */}
      <div className="forge-tabs" style={{ margin: '16px 0' }}>
        {(['overview', 'session', 'delegate', 'negotiate', 'resolve'] as const).map(s => (
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
        <div className="dashboard-section">
          <div style={{ padding: '20px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}`, marginBottom: 16 }}>
            <h3 style={{ color: themeColors.text }}>Negotiation Overview</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12 }}>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_sessions}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Total Rounds</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: themeColors.primary }}>{stats.total_rounds}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Active Sessions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#22c55e' }}>{stats.active_sessions}</div>
              </div>
              <div style={{ padding: 12, background: '#fff', borderRadius: 6, border: `1px solid ${themeColors.border}` }}>
                <div style={{ fontWeight: 600, color: themeColors.text }}>Resolved</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#8b5cf6' }}>{stats.resolved_sessions}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Session */}
      {activeSection === 'session' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Create Negotiation Session</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Topic *</label>
              <input
                type="text"
                value={sessionForm.topic}
                onChange={e => setSessionForm(f => ({ ...f, topic: e.target.value }))}
                placeholder="e.g., Resource Allocation Strategy"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                rows={3}
                value={sessionForm.description}
                onChange={e => setSessionForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the negotiation context and goals..."
              />
            </div>
            <div className="form-group">
              <label>Strategy</label>
              <select value={sessionForm.strategy} onChange={e => setSessionForm(f => ({ ...f, strategy: e.target.value }))}>
                {STRATEGIES.map(s => (
                  <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleCreateSession}
              disabled={!sessionForm.topic.trim()}
            >
              Create Session
            </button>
          </div>
        </div>
      )}

      {/* Delegate */}
      {activeSection === 'delegate' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Add Delegate</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session ID *</label>
              <input
                type="text"
                value={delegateForm.session_id}
                onChange={e => setDelegateForm(f => ({ ...f, session_id: e.target.value }))}
                placeholder="Enter session ID"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={delegateForm.name}
                  onChange={e => setDelegateForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Delegate name"
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select value={delegateForm.role} onChange={e => setDelegateForm(f => ({ ...f, role: e.target.value }))}>
                  {DELEGATE_ROLES.map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Stance</label>
                <input
                  type="text"
                  value={delegateForm.stance}
                  onChange={e => setDelegateForm(f => ({ ...f, stance: e.target.value }))}
                  placeholder="Delegate's position on the topic"
                />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <input
                  type="number"
                  value={delegateForm.priority}
                  onChange={e => setDelegateForm(f => ({ ...f, priority: e.target.value }))}
                  placeholder="Priority level"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleAddDelegate}
              disabled={!delegateForm.session_id.trim() || !delegateForm.name.trim()}
            >
              Add Delegate
            </button>
          </div>
        </div>
      )}

      {/* Negotiate */}
      {activeSection === 'negotiate' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Submit Proposal</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={proposeForm.session_id}
                  onChange={e => setProposeForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session ID"
                />
              </div>
              <div className="form-group">
                <label>Delegate ID *</label>
                <input
                  type="text"
                  value={proposeForm.delegate_id}
                  onChange={e => setProposeForm(f => ({ ...f, delegate_id: e.target.value }))}
                  placeholder="Delegate ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>Content *</label>
              <textarea
                rows={3}
                value={proposeForm.content}
                onChange={e => setProposeForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Proposal content..."
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Rationale</label>
                <input
                  type="text"
                  value={proposeForm.rationale}
                  onChange={e => setProposeForm(f => ({ ...f, rationale: e.target.value }))}
                  placeholder="Reasoning behind this proposal"
                />
              </div>
              <div className="form-group">
                <label>Confidence (0-1)</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={proposeForm.confidence}
                  onChange={e => setProposeForm(f => ({ ...f, confidence: e.target.value }))}
                  placeholder="0.0 - 1.0"
                />
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handlePropose}
              disabled={!proposeForm.session_id.trim() || !proposeForm.delegate_id.trim() || !proposeForm.content.trim()}
            >
              Submit Proposal
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Cast Vote</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-row">
              <div className="form-group">
                <label>Session ID *</label>
                <input
                  type="text"
                  value={voteForm.session_id}
                  onChange={e => setVoteForm(f => ({ ...f, session_id: e.target.value }))}
                  placeholder="Session ID"
                />
              </div>
              <div className="form-group">
                <label>Proposal ID *</label>
                <input
                  type="text"
                  value={voteForm.proposal_id}
                  onChange={e => setVoteForm(f => ({ ...f, proposal_id: e.target.value }))}
                  placeholder="Proposal ID"
                />
              </div>
              <div className="form-group">
                <label>Delegate ID *</label>
                <input
                  type="text"
                  value={voteForm.delegate_id}
                  onChange={e => setVoteForm(f => ({ ...f, delegate_id: e.target.value }))}
                  placeholder="Delegate ID"
                />
              </div>
            </div>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={voteForm.approve}
                  onChange={e => setVoteForm(f => ({ ...f, approve: e.target.checked }))}
                />
                {' '}Approve
              </label>
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleVote}
              disabled={!voteForm.session_id.trim() || !voteForm.proposal_id.trim() || !voteForm.delegate_id.trim()}
            >
              Cast Vote
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Deliberate</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session ID *</label>
              <input
                type="text"
                value={deliberateForm.session_id}
                onChange={e => setDeliberateForm(f => ({ ...f, session_id: e.target.value }))}
                placeholder="Session ID"
              />
            </div>
            <div className="form-group">
              <label>Summary *</label>
              <textarea
                rows={3}
                value={deliberateForm.summary}
                onChange={e => setDeliberateForm(f => ({ ...f, summary: e.target.value }))}
                placeholder="Summary of deliberation points..."
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleDeliberate}
              disabled={!deliberateForm.session_id.trim() || !deliberateForm.summary.trim()}
            >
              Submit Deliberation
            </button>
          </div>
        </div>
      )}

      {/* Resolve */}
      {activeSection === 'resolve' && (
        <div className="dashboard-section">
          <h3 style={{ color: themeColors.text }}>Resolve Session</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session ID *</label>
              <input
                type="text"
                value={resolveSessionId}
                onChange={e => setResolveSessionId(e.target.value)}
                placeholder="Enter session ID to resolve"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleResolve}
              disabled={!resolveSessionId.trim()}
            >
              Resolve Session
            </button>
          </div>

          <h3 style={{ color: themeColors.text, marginTop: 24 }}>Get Session Summary</h3>
          <div className="skill-execute" style={{ marginBottom: 16, position: 'static' }}>
            <div className="form-group">
              <label>Session ID *</label>
              <input
                type="text"
                value={summarySessionId}
                onChange={e => setSummarySessionId(e.target.value)}
                placeholder="Enter session ID to get summary"
              />
            </div>
            <button
              className="btn-primary"
              style={{ background: themeColors.primary }}
              onClick={handleGetSummary}
              disabled={!summarySessionId.trim()}
            >
              Get Summary
            </button>
          </div>

          {summaryResult && (
            <div style={{ padding: '16px', background: themeColors.bg, borderRadius: 8, border: `1px solid ${themeColors.border}` }}>
              <h4 style={{ color: themeColors.text }}>Session Summary</h4>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: themeColors.text }}>{JSON.stringify(summaryResult, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NegotiationPanel;